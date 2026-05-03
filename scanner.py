#!/usr/bin/env python3
"""
Market Scanner — 4 kaynak fırsat analizi
Kullanım: python3 scanner.py
Not: PRODUCTHUNT_TOKEN .env dosyasında veya environment variable olarak olmalı
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# .env varsa yükle (lokal çalışma için), yoksa environment variable kullan (GitHub Actions için)
load_dotenv()


# ── Product Hunt ───────────────────────────────────────────────
def fetch_producthunt(token, limit=10):
    query = """
    query($first: Int!) {
      posts(order: VOTES, first: $first) {
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
        json={"query": query, "variables": {"first": limit}},
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
            startups.append({"name": name, "description": description[:200], "url": url})
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
        return posts[:limit]


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
    results = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "sources": {},
    }

    print("🔍 Product Hunt taranıyor...")
    if token:
        try:
            results["sources"]["producthunt"] = fetch_producthunt(token)
            print(f"   ✅ {len(results['sources']['producthunt'])} ürün bulundu")
        except Exception as e:
            print(f"   ❌ Hata: {e}")
            results["sources"]["producthunt"] = []
    else:
        print("   ⚠️  PRODUCTHUNT_TOKEN ayarlanmamış, atlanıyor")
        results["sources"]["producthunt"] = []

    print("🔍 Hacker News (Show HN) taranıyor...")
    try:
        results["sources"]["hackernews"] = fetch_hackernews()
        print(f"   ✅ {len(results['sources']['hackernews'])} post bulundu")
    except Exception as e:
        print(f"   ❌ Hata: {e}")
        results["sources"]["hackernews"] = []

    print("🔍 BetaList taranıyor...")
    try:
        results["sources"]["betalist"] = fetch_betalist()
        print(f"   ✅ {len(results['sources']['betalist'])} startup bulundu")
    except Exception as e:
        print(f"   ❌ Hata: {e}")
        results["sources"]["betalist"] = []

    print("🔍 Indie Hackers taranıyor...")
    try:
        results["sources"]["indiehackers"] = fetch_indiehackers()
        print(f"   ✅ {len(results['sources']['indiehackers'])} post bulundu")
    except Exception as e:
        print(f"   ❌ Hata: {e}")
        results["sources"]["indiehackers"] = []

    # scans/ klasörüne ISO tarih + saat formatında kaydet
    script_dir = Path(__file__).parent
    scans_dir = script_dir / "scans"
    scans_dir.mkdir(exist_ok=True)

    # Eski dosyaları temizle (30 gün+)
    cleanup_old_scans(scans_dir, keep_days=30)

    # UTC zaman damgası kullan (GitHub Actions UTC'de çalışır, tutarlılık için)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    out_file = scans_dir / f"scan_{timestamp}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Tamamlandı — sonuçlar kaydedildi: {out_file.name}")


if __name__ == "__main__":
    main()
