---
name: market-scanner
description: Use when generating the daily market opportunity report. Reads the latest scan JSON from the scans/ directory (already produced by GitHub Actions, with deduplication), filters by quality criteria, ranks by score, and writes a categorized markdown report to reports/.
---

## Bağlam

GitHub Actions her sabah otomatik olarak `scanner.py`'yi çalıştırır ve `scans/` klasörüne yeni bir JSON dosyası ekler. JSON içeriği **deduplikasyondan geçmiş** — yani daha önce raporlanmış ürünler zaten elenmiş, sadece **yeni** ürünler gelir.

Senin görevin **scanner'ı çalıştırmak değil**, hazır JSON'u okuyup filtreli rapor üretmektir.

## Adımlar

### 1. En güncel JSON'u bul

`scans/` klasöründeki dosyalar `scan_YYYY-MM-DD_HHMM.json` formatında. **En son timestamp'li olanı** seç ve oku.

### 2. JSON'daki veri miktarını değerlendir

JSON'un üst kısmında `stats` alanı var, her kaynak için `new` sayısı gösterir:

```json
"stats": {
  "producthunt": {"raw": 10, "new": 3},
  "hackernews": {"raw": 15, "new": 12},
  ...
}
```

**Toplam yeni ürün sayısına göre rapor uzunluğu:**

- **0-2 yeni ürün varsa:** Çok kısa rapor — "Bugün yeni fırsat yok / sadece şu 1-2 fikir var" diye not düş, varsa olanları göster.
- **3-7 yeni ürün varsa:** Kısa rapor, hepsini değerlendir.
- **8+ yeni ürün varsa:** Normal rapor, seçici filtreleme uygula.

**Hayalî fikir uydurma. JSON'da olmayanı yazma.** Az veri geldiyse az yaz.

### 3. Raporu yaz

Aşağıdaki kurallara göre markdown raporu üret.

**Amaç:** Bir girişimciye **ilham verecek** raporu hazırlıyorsun. Kaynaklarda gördüğün fikirlerden iyi, kayda değer, yaratıcı olanları öne çıkar — okuyan "vay be, bu güzel fikirmiş" ya da "şuna kafa yormamışım" desin. **İnovatif olmak şart değil; basit ama daha önce düşünülmemiş bir açı da değerli.**

#### Filtreleme — seçici uygula

Şunları **ele**:

- **Saf altyapı / niş geliştirici araçları** — örn: "Rust ile Kubernetes yeniden yazıldı", "Postgres üzerinde private GitHub", "Terminal email client". Bunlar iş fikri değil, geliştirici hobi projeleri.
- **Açıklaması olmayan, ne işe yaradığı belli olmayan girişimler** — başlığı kriptik, tagline'ı yok.
- **Trolllük, şaka projeleri, meme ürünler** — örn: "AI talking fruit videos", "matchstick puzzle builder".
- **Birebir kopyalar** — taze bir açısı, twist'i veya farklı bir kullanıcı kitlesi olmayan klonlar. *Aynı kategoride başka ürünler olması tek başına eleme sebebi değil — yaklaşım orijinalse al.*
- **Indie Hackers'taki "ben şunu yaptım" hikayeleri** — post sadece launch/yol hikayesi anlatıyor, altında somut bir ürün/fikir durmuyorsa ele. Ama post bir ürün/fikir tanıtıyorsa, hikaye çerçevesinde olsa bile al.

**Tutmak için kriter:** Yaratıcı bir açı + ilham verici. Basit-ama-orijinal de değerli; illa büyük iş modeli aranmıyor.

#### Sıralama

Kalanları **puana göre azalan** sırala:
- Product Hunt: `votes`
- Hacker News: `points` (tiebreak: `comments`)
- BetaList: skor yok, listede geldikleri sırayla
- Indie Hackers: `votes` varsa ona göre, yoksa listede geldikleri sırayla

Kategori içinde de puanı yüksek olan üstte olsun.

#### Her fikir için format

- **Başlık satırı:** `### Ürün adı ([Kaynak](url))`
- **Açıklama:** 2-3 cümle. Ne yaptığını + neden ilginç + hangi acıyı çözdüğünü sade bir dille anlat. Marketing dili yok, pitch deck dili yok.
- **Metrik satırı:** Varsa oy/puan + yorum sayısı, italik tek satır

Her fikir aynı formatta görünmeli. Bazılarında açıklama olup bazılarında olmaması kabul değil — açıklama yapamayacağın ürünü zaten rapora alma.

#### Gruplama

Kaynak bazlı **değil**, fikir kategorisine göre grupla. Örnek kategoriler:
- AI / Yapay Zeka
- Verimlilik
- Geliştirici Araçları
- B2B SaaS
- Fintech
- Marketplace
- Consumer App
- Sağlık / Wellness
- Eğitim
- Diğer

**Kural:** "Diğer" kategorisi 5 maddeyi geçerse, içindeki maddeleri yeni alt kategorilere böl. 5 maddeden az ise olduğu gibi kalsın.

### 4. Raporu kaydet

`reports/report_YYYY-MM-DD.md` olarak kaydet (UTC tarihi). Aynı gün için zaten rapor varsa **üzerine yaz**. Günde tek rapor.

Rapor başlığı:
```markdown
# Market Scanner — YYYY-MM-DD

Bugün X yeni içerik geldi (ham toplam: Y), Z fırsat seçildi.

---
```

Sonunda:
```markdown
---
*Oluşturulma: YYYY-MM-DD HH:MM UTC*
```

### 5. Commit

Raporu repo'ya commit et:
- Commit mesajı: `Daily report: YYYY-MM-DD`
- Branch: `main`
