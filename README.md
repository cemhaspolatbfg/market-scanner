# Market Scanner

ABD/Avrupa pazarındaki yeni ürünleri Türkiye pazarı perspektifiyle her sabah otomatik tarayan ve raporlayan sistem.

## Mimari

```
06:00 UTC (TR 09:00) → GitHub Actions
                       └→ scanner.py (cloud)
                       └→ 4 kaynaktan veri çek
                       └→ state/seen.json'a göre dedup
                       └→ scans/ klasörüne yeni ürünleri JSON olarak yaz
                       └→ commit + push (scans/ + state/)

07:00 UTC (TR 10:00) → Claude Routine
                       └→ En yeni JSON'u oku
                       └→ Filtrele ve kategorize et
                       └→ reports/ klasörüne markdown
                       └→ commit + push

İstediğin zaman → git pull → reports/ klasörü güncel
```

## Kaynaklar

- **Product Hunt** — son 7 gün içinde launch olan, en çok oy alan 10 ürün (API)
- **Hacker News** — son 24 saatte "Show HN" postları (Algolia API)
- **BetaList** — yeni eklenen startuplar (scrape)
- **Indie Hackers** — haftanın trend gönderileri (Playwright)

## Deduplikasyon

`state/seen.json` dosyası daha önce raporlanmış her ürünün ID'sini ve görüldüğü tarihi tutar. Scanner her çalıştığında:

1. seen.json'ı yükler
2. Her kaynaktan veri çeker
3. Daha önce görülen ID'leri filtreler (sadece yeni olanlar JSON'a gider)
4. Yeni ID'leri seen.json'a ekler
5. 90 günden eski entry'leri otomatik temizler (yeniden trending olursa tekrar değerlendirilebilsin)

Yani bir ürün rapora bir kez girdiğinde 90 gün boyunca tekrar görünmez. Bu sürenin sonunda hâlâ trend ise yeni bir fırsat olarak yeniden değerlendirilir.

## Kurulum

### 1. Repo'yu GitHub'a yükle (yapıldı)

### 2. GitHub Secret ekle (yapıldı)

`PRODUCTHUNT_TOKEN` repo secrets'ında.

### 3. Claude Routine kur

`claude.ai/code` → Routines → Create routine:

- **Repo:** market-scanner
- **Cadence:** Daily, 07:00 UTC
- **Environment:** Trusted (GitHub erişimi yeterli)
- **Prompt:** (aşağıda)

#### Routine prompt'u

```
Bugünün market raporunu hazırla.

1. scans/ klasöründeki en yeni scan_YYYY-MM-DD_HHMM.json 
   dosyasını oku.

2. JSON'daki "stats" alanına bak. Toplam yeni ürün sayısı 
   azsa rapor da kısa olsun. SKILL.md'deki kurallara uy. 
   Hayalî fikir uydurma.

3. Repo'daki SKILL.md dosyasındaki filtreleme kurallarını 
   agresif uygula — Türkiye pazarı için gerçek fırsat olan 
   fikirleri seç.

4. Raporu reports/report_YYYY-MM-DD.md olarak kaydet 
   (bugünün UTC tarihi).

5. Repo'ya commit et:
   - Commit mesajı: "Daily report: YYYY-MM-DD"
   - Branch: main
```

## Lokal kullanım (opsiyonel)

Manuel çalıştırmak istersen:

```bash
# Bağımlılıklar
pip install -r requirements.txt
playwright install chromium

# .env oluştur (zaten var)
echo "PRODUCTHUNT_TOKEN=your_token_here" > .env

# Çalıştır
python3 scanner.py
```

## Klasör yapısı

```
market_scanner/
├── .github/
│   └── workflows/
│       └── scanner.yml       # GitHub Actions workflow
├── scanner.py                # Veri çekme + dedup
├── SKILL.md                  # Routine için talimat
├── requirements.txt          # Python bağımlılıkları
├── .env                      # PRODUCTHUNT_TOKEN (gitignore'da, sadece lokal)
├── .gitignore
├── README.md
├── scans/                    # Ham JSON çıktıları (sadece yeni ürünler)
│   └── scan_YYYY-MM-DD_HHMM.json
├── state/                    # Persistent state (dedup için)
│   └── seen.json
└── reports/                  # İşlenmiş markdown raporlar
    └── report_YYYY-MM-DD.md
```

## Bakım

- Scanner 30 günden eski JSON dosyalarını otomatik siler
- seen.json'da 90 günden eski entry'ler otomatik temizlenir
- Tüm zaman damgaları UTC
- Rapor günde tek tane (üzerine yazılır)
- GitHub Actions ücretsiz quota: aylık 2000 dakika
