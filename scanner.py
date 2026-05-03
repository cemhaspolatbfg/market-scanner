#!/usr/bin/env python3
"""
Market Scanner — 4 kaynak fırsat analizi
Kullanım: python3 scanner.py
Not: PRODUCTHUNT_TOKEN .env dosyasında veya environment variable olarak olmalı

Deduplikasyon mantığı:
- Daha önce raporlanan her ürünün ID'si state/seen.json'da tutulur
- Her kaynaktan veri çekildikten sonra, daha önce görülen ID'ler filtrelenir
- JSON'a sadece YENİ ürünler yazılır
- 90 günden eski seen entry'leri otomatik temizlenir (yeniden trending olursa
  tekrar değerlendirilebilsin diye)
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

load_dotenv()

# Seen entry'lerini ne kadar süre saklayalım
SEEN_RETENTION_DAYS = 90


# ── Seen state yönetimi ────────────────────────────────────────
def load_seen(state_dir):
    """state/seen.json'ı yükle, yoksa boş yapı dön."""
    seen_file = state_dir / "seen.json"
    if not seen_file.exists():
        return {
            "producthunt": {},
            "hackernews": {},
            "betalist": {},
            "indiehackers": {},
        }
    with open(seen_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_seen(state_dir, seen):
    """state/seen.json'a yaz."""
    state_dir.mkdir(exist_ok=True)
    seen_file = state_dir / "seen.json"
    with open(seen_file, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2, sort_keys=True)


def cleanup_seen(seen, retention_days=SEEN_RETENTION_DAYS):
    """retention_days'den eski entry'leri sil."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).date()
    deleted = 0
    for source in seen:
        to_delete = []
        for item_id, date_str in seen[source].items():
            try:
                seen_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if seen_date < cutoff:
                    to_delete.append(item_id)
            except ValueError:
                # Bozuk tarih varsa sil
                to_delete.append(item_id)
        for item_id in to_delete:
            del seen[source][item_id]
            deleted += 1
    if deleted > 0:
        print(f"🧹 {deleted} eski seen entry silindi (>{retention_days} gün)")


# ── Product Hunt ───────────────────────────────────────────────
def fetch_producthunt(token, days=7, limit=10):
    """Son `days` gün içinde launch olan, en çok oy alan ürünleri getir."""
    posted_after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    query = """
    query($first: Int!, $postedAfter: DateTime!) {
      posts(order: VOTES, first: $first, postedAfter: $postedAfter) {
        edges {
          node {
            name
            tagline
            description
            votesCount
            slug
            website
            topics {
              edges { node { name } }
            }
          }
        }
      }
    }
    """
    resp = requests.post(
        "https://api.producthunt.com/v2/api/graphql",
        json={
            "query": query,
            "variables": {"first": limit, "postedAfter": posted_after},
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    posts = data["data"]["posts"]["edges"]
    return [
        {
            "id": p["node"]["slug"],  # Stable ID for dedup
            "name": p["node"]["name"],
            "tagline": p["node"]["tagline"],
            "description": p["node"].get("description", ""),
            "votes": p["node"]["votesCount"],
            "ph_url": f"https://www.producthunt.com/posts/{p['node']['slug']}",
            "website": p["node"].get("website", ""),
            "topics": [t["node"]["name"] for t in p["node"]["topics"]["edges"]],
            "source": "Product Hunt",
        }
        for p in posts
    ]


# ── Hacker News (Show HN) ──────────────────────────────────────
def fetch_hackernews(hours=24, limit=15):
    since = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    resp = requests.get(
        "https://hn.algolia.com/api/v1/search",
        params={
            "tags": "show_hn",
            "numericFilters": f"created_at_i>{since}",
            "hitsPerPage": limit,
        },
        timeout=15,
    )
    resp.raise_for_status()
    hits = resp.json()["hits"]
    return [
        {
            "id": h["objectID"],  # Stable ID for dedup
            "name": h.get("title", ""),
            "url": h.get("url", ""),
            "points": h.get("points", 0),
            "comments": h.get("num_comments", 0),
            "hn_url": f"https://news.ycombinator.com/item?id={h['objectID']}",
        }
        for h in hits
    ]


# ── BetaList ───────────────────────────────────────────────────
def fetch_betalist(limit=15):
    resp = requests.get(
        "https://betalist.com/",
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        timeout=15,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    startups = []
    seen = set()

    startup_links = [a for a in soup.find_all("a", href=True) if "/startups/" in a["href"]]
    for link in startup_links:
        href = link["href"]
        if href in seen:
            continue
        seen.add(href)

        name = link.get_text(strip=True)
        description = ""

        parent = link.parent
        for _ in range(5):
            if parent is None:
                break
            full_text = parent.get_text(" ", strip=True)
            if len(full_text) > len(name) + 5:
                description = full_text.replace(name, "").strip()
                break
            parent = parent.parent

        url = ("https://betalist.com" + href) if href.startswith("/") else href
        if name:
            startups.append({
                "id": href,  # Stable ID for dedup (path)
                "name": name,
                "description": description[:200],
                "url": url,
            })
        if len(startups) >= limit:
            break

    return startups


# ── Indie Hackers ──────────────────────────────────────────────
def fetch_indiehackers(limit=15):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page.goto(
            "https://www.indiehackers.com/?filter=top&period=weekly",
            wait_until="load",
            timeout=45000,
        )
        page.wait_for_timeout(4000)

        try:
            page.click('button:has-text("Accept")', timeout=3000)
            page.wait_for_timeout(2000)
        except Exception:
            pass

        posts = page.evaluate("""() => {
            const skipWords = ['privacy', 'cookie', 'consent', 'manage', 'performance'];
            const headings = Array.from(document.querySelectorAll('h2, h3'));
            return headings
                .map(el => {
                    const title = el.innerText.trim();
                    const anchor = el.closest('a') || el.querySelector('a') || el.parentElement?.querySelector('a');
                    return {
                        title: title,
                        url: anchor?.href || '',
                        votes: '—',
                    };
                })
                .filter(p =>
                    p.title.length > 10 &&
                    !skipWords.some(w => p.title.toLowerCase().includes(w))
                );
        }""")

        browser.close()

        # Add stable ID (use URL since IH posts have unique URLs)
        result = []
        for post in posts[:limit]:
            if post.get("url"):
                result.append({
                    "id": post["url"],  # Stable ID for dedup
                    "title": post["title"],
                    "url": post["url"],
                    "votes": post.get("votes", "—"),
                })
        return result


# ── Deduplikasyon ──────────────────────────────────────────────
def filter_unseen(items, source_name, seen):
    """Daha önce görülmemiş itemları döndürür, seen'i günceller."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_items = []
    for item in items:
        item_id = item.get("id")
        if not item_id:
            continue  # ID'siz itemları atla
        if item_id not in seen[source_name]:
            new_items.append(item)
            seen[source_name][item_id] = today
    return new_items


# ── Eski scan dosyalarını temizle ──────────────────────────────
def cleanup_old_scans(scans_dir, keep_days=30):
    """30 günden eski scan dosyalarını siler."""
    cutoff = datetime.now() - timedelta(days=keep_days)
    deleted = 0
    for f in scans_dir.glob("scan_*.json"):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()
            deleted += 1
    if deleted > 0:
        print(f"🧹 {deleted} eski scan dosyası silindi (>{keep_days} gün)")


# ── Ana akış ───────────────────────────────────────────────────
def main():
    token = os.environ.get("PRODUCTHUNT_TOKEN")
    script_dir = Path(__file__).parent
    scans_dir = script_dir / "scans"
    state_dir = script_dir / "state"
    scans_dir.mkdir(exist_ok=True)
    state_dir.mkdir(exist_ok=True)

    # Seen'i yükle ve eski entry'leri temizle
    seen = load_seen(state_dir)
    cleanup_seen(seen)

    results = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "sources": {},
        "stats": {},
    }

    # Product Hunt
    print("🔍 Product Hunt (son 7 gün) taranıyor...")
    if token:
        try:
            raw = fetch_producthunt(token, days=7)
            new = filter_unseen(raw, "producthunt", seen)
            results["sources"]["producthunt"] = new
            results["stats"]["producthunt"] = {"raw": len(raw), "new": len(new)}
            print(f"   ✅ {len(raw)} ham, {len(new)} yeni")
        except Exception as e:
            print(f"   ❌ Hata: {e}")
            results["sources"]["producthunt"] = []
            results["stats"]["producthunt"] = {"raw": 0, "new": 0, "error": str(e)}
    else:
        print("   ⚠️  PRODUCTHUNT_TOKEN ayarlanmamış, atlanıyor")
        results["sources"]["producthunt"] = []
        results["stats"]["producthunt"] = {"raw": 0, "new": 0, "skipped": True}

    # Hacker News
    print("🔍 Hacker News (Show HN, son 24 saat) taranıyor...")
    try:
        raw = fetch_hackernews()
        new = filter_unseen(raw, "hackernews", seen)
        results["sources"]["hackernews"] = new
        results["stats"]["hackernews"] = {"raw": len(raw), "new": len(new)}
        print(f"   ✅ {len(raw)} ham, {len(new)} yeni")
    except Exception as e:
        print(f"   ❌ Hata: {e}")
        results["sources"]["hackernews"] = []
        results["stats"]["hackernews"] = {"raw": 0, "new": 0, "error": str(e)}

    # BetaList
    print("🔍 BetaList taranıyor...")
    try:
        raw = fetch_betalist()
        new = filter_unseen(raw, "betalist", seen)
        results["sources"]["betalist"] = new
        results["stats"]["betalist"] = {"raw": len(raw), "new": len(new)}
        print(f"   ✅ {len(raw)} ham, {len(new)} yeni")
    except Exception as e:
        print(f"   ❌ Hata: {e}")
        results["sources"]["betalist"] = []
        results["stats"]["betalist"] = {"raw": 0, "new": 0, "error": str(e)}

    # Indie Hackers
    print("🔍 Indie Hackers (haftalık top) taranıyor...")
    try:
        raw = fetch_indiehackers()
        new = filter_unseen(raw, "indiehackers", seen)
        results["sources"]["indiehackers"] = new
        results["stats"]["indiehackers"] = {"raw": len(raw), "new": len(new)}
        print(f"   ✅ {len(raw)} ham, {len(new)} yeni")
    except Exception as e:
        print(f"   ❌ Hata: {e}")
        results["sources"]["indiehackers"] = []
        results["stats"]["indiehackers"] = {"raw": 0, "new": 0, "error": str(e)}

    # Seen'i kaydet
    save_seen(state_dir, seen)

    # Eski scan dosyalarını temizle
    cleanup_old_scans(scans_dir, keep_days=30)

    # JSON'u kaydet
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    out_file = scans_dir / f"scan_{timestamp}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total_new = sum(s.get("new", 0) for s in results["stats"].values())
    print(f"\n✅ Tamamlandı — {total_new} yeni fikir, dosya: {out_file.name}")


if __name__ == "__main__":
    main()
