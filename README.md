# Market Scanner

ABD/Avrupa pazarındaki yeni ürünleri Türkiye pazarı perspektifiyle her sabah otomatik tarayan ve raporlayan sistem.

## Mimari

```
06:00 UTC (TR 09:00) → GitHub Actions
                       └→ scanner.py (cloud)
                       └→ scans/ klasörüne JSON
                       └→ commit + push

07:00 UTC (TR 10:00) → Claude Routine
                       └→ En yeni JSON'u oku
                       └→ Filtrele ve kategorize et
                       └→ reports/ klasörüne markdown
                       └→ commit + push

İstediğin zaman → git pull → reports/ klasörü güncel
```

## Kaynaklar

- **Product Hunt** — günün en çok oy alan 10 ürünü (API)
- **Hacker News** — son 24 saatte "Show HN" postları (Algolia API)
- **BetaList** — yeni eklenen startuplar (scrape)
- **Indie Hackers** — haftanın trend gönderileri (Playwright)

## Kurulum

### 1. Repo'yu GitHub'a yükle

```bash
cd /Users/cemhaspolat/Desktop/claude/market_scanner
git init
git add .
git commit -m "Initial commit"
gh repo create market-scanner --private --source=. --push
```

### 2. GitHub Secret ekle

Product Hunt API token'ını GitHub Secret olarak ekle:

1. Repo → Settings → Secrets and variables → Actions
2. "New repository secret"
3. Name: `PRODUCTHUNT_TOKEN`
4. Value: Senin token'ın

Token nereden alınır: https://www.producthunt.com/v2/oauth/applications

### 3. GitHub Actions test et

İlk çalıştırmayı manuel tetikle:
1. Repo → Actions → "Daily Market Scan"
2. "Run workflow" → main branch → çalıştır
3. Birkaç dakika bekle, `scans/` klasöründe yeni dosya görmen lazım

### 4. Claude Routine kur

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

2. Repo'daki SKILL.md dosyasındaki kurallara göre filtreli, 
   kategorize edilmiş bir rapor üret. Filtreleme kurallarını 
   agresif uygula — Türkiye pazarı için gerçek fırsat olan 
   8-15 fikri seç.

3. Raporu reports/report_YYYY-MM-DD.md olarak kaydet 
   (bugünün UTC tarihi).

4. Repo'ya commit et:
   - Commit mesajı: "Daily report: YYYY-MM-DD"
   - Branch: main
```

## Lokal kullanım (opsiyonel)

Manuel çalıştırmak istersen:

```bash
# Bağımlılıklar
pip install -r requirements.txt
playwright install chromium

# .env oluştur
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
├── scanner.py                # Veri çekme scripti
├── SKILL.md                  # Routine için talimat
├── requirements.txt          # Python bağımlılıkları
├── .env                      # PRODUCTHUNT_TOKEN (gitignore'da, sadece lokal)
├── .gitignore
├── README.md
├── scans/                    # Ham JSON çıktıları (tracked)
│   └── scan_YYYY-MM-DD_HHMM.json
└── reports/                  # İşlenmiş markdown raporlar (tracked)
    └── report_YYYY-MM-DD.md
```

## Bakım

- Scanner 30 günden eski JSON dosyalarını otomatik siler
- Tüm zaman damgaları UTC (GitHub Actions UTC'de çalışır)
- Rapor günde tek tane (üzerine yazılır)
- GitHub Actions ücretsiz quota: aylık 2000 dakika (bu workflow ~2 dk → bol bol yeter)
