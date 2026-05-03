---
name: market-scanner
description: Use when generating the daily market opportunity report. Reads the latest scan JSON from the scans/ directory (already produced by GitHub Actions), filters for Turkish-market opportunities, and writes a categorized markdown report to reports/.
---

## Bağlam

GitHub Actions her sabah otomatik olarak `scanner.py`'yi çalıştırır ve `scans/` klasörüne yeni bir JSON dosyası ekler. Senin görevin **scanner'ı çalıştırmak değil**, hazır JSON'u okuyup filtreli rapor üretmektir.

## Adımlar

### 1. En güncel JSON'u bul

`scans/` klasöründeki dosyalar `scan_YYYY-MM-DD_HHMM.json` formatında. **En son timestamp'li olanı** seç ve oku.

### 2. Raporu yaz

JSON'daki ham veriyi kullanarak aşağıdaki kurallara göre markdown raporu üret.

**Amaç:** Okuyan kişi "aa bu iyi fikir", "bunu Türkiye'ye getirmeliyim" desin. Yatırım yapmayı bekleyen bir girişimciye sunulacak rapor gibi düşün.

#### Filtreleme — agresif uygula

Scanner ham 30-40 sonuç getirir. **Bunların çoğu rapora girmemeli.** Türkiye pazarı için fırsat olabilecek 8-15 maddeyi seç. Şunları **ele**:

- **Saf altyapı / niş geliştirici araçları** — örn: "Rust ile Kubernetes yeniden yazıldı", "Postgres üzerinde private GitHub", "Terminal email client". Bunlar iş fikri değil, hobby projeleri.
- **Açıklaması olmayan, ne işe yaradığı belli olmayan girişimler** — başlığı kriptik, tagline'ı yok.
- **Türkiye'de ölçeklemesi imkansız niş ürünler** — örn: ABD'ye özgü polis radyosu, ABD eyalet seçim sistemleri.
- **Trolllük, şaka projeleri, meme ürünler** — örn: "AI talking fruit videos", "matchstick puzzle builder".
- **Mevcut araçların çok benzeri kopyaları** — pazarda zaten 10 muadili olan SaaS klonları.
- **Indie Hackers'taki "ben şunu yaptım" tarzı blog post'ları** — eğer içerik bir iş fikri değil sadece bir hikaye ise (örn: "PH'de launch ettim, şu oldu") rapora alma. Ama içeriği gerçek bir iş modeli/niş anlatıyorsa al (örn: "$15M ARR kazandığım brick-and-mortar gap'i").

**Tutmak için kriter:** Açık bir problem çözüyor + iş modeli net + Türkiye'de muadili yok veya zayıf + ölçeklenebilir.

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

### 3. Raporu kaydet

`reports/report_YYYY-MM-DD.md` olarak kaydet (UTC tarihi). Aynı gün için zaten rapor varsa **üzerine yaz**. Günde tek rapor.

Rapor başlığı:
```markdown
# Market Scanner — YYYY-MM-DD

Bugün X kaynaktan Y ham içerik tarandı, Türkiye pazarı için Z fırsat seçildi.

---
```

Sonunda:
```markdown
---
*Oluşturulma: YYYY-MM-DD HH:MM UTC*
```

### 4. Commit

Raporu repo'ya commit et:
- Commit mesajı: `Daily report: YYYY-MM-DD`
- Branch: `main`
