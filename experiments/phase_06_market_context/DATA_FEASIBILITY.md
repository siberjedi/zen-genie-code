# DATA FEASIBILITY — kaynak bazında erişim, kapsama, maliyet

İndirme YAPILMADI. Aşağıdakiler dokümantasyon + API referans taramasına dayanır
(2026-09-08). "NO 2025H1 DOWNLOAD" — planlar 2023-06-30 sonrasını kapsamaz.

## A) Cross-asset klines — FEASIBLE (ücretsiz, tam)

- **Provider:** data.binance.vision (resmi Binance public data).
- **Method:** monthly zip (`data/spot/monthly/klines/{SYM}/5m/` + um futures),
  checksum dosyaları mevcut; `download-kline.py -t spot -s ETHUSDT… -i 5m`.
- **Semboller:** ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, ADAUSDT, DOGEUSDT…
  (SOL 2020-08'den; diğerleri 2017–2019'dan listeli).
- **Coverage:** 2020-01-01 → 2023-06-30 TAM (aylık dosyalar; günlük dosyalarla
  tamamlama mümkün).
- **Size:** 5m kline ≈ 105k satır/yıl/sembol → 3.5 yıl × ~8 sembol ≈ 3M satır,
  < 500 MB zipsiz. CPU: Phase 5 feature build ile aynı mertebe.
- **Timestamp:** exchange clock, BTC feed ile aynı; hizalama trivial.
- **Quality checks:** checksum verify, missing-month taraması, duplicated
  close-time kontrolü, delist/sembol-değişimi kontrolü.
- **Legal/repro:** public data, ToS uyumlu; URL + checksum → tam reproducible.

## B) Funding — FEASIBLE (ücretsiz, tam)

- **Provider:** Binance USDⓈ-M REST `GET /fapi/v1/fundingRate`
  (symbol, startTime, endTime, limit≤1000, sayfalama).
- **Coverage:** BTCUSDT perp listeleme ~Eylül 2019 → 2020-01-01 → 2023-06-30 TAM.
  8h settlement (00:00/08:00/16:00 UTC) → ~3 nokta/gün → 3.5 yıl ≈ 3.8k satır.
- **Size:** ihmal edilebilir (KB'lar). CPU: ihmal edilebilir.
- **Timestamp:** `fundingTime` = settlement anı; o andaki değer KESİN olarak
  bilinir (premium TWAP kapanışı). Kural: fundingTime=T değeri yalnızca
  close ≥ T candle'larında kullanılır (LEAKAGE_MATRIX B1).
- **Quality checks:** 8h grid düzenliliği, eksik settlement taraması
  (bakım kesintileri), outlier (|rate| > %1) incelemesi.
- **Legal/repro:** public REST, keyless; istek pencereleri + ham JSON saklanır.

## C) Open interest — PARTLY FEASIBLE (günlük ücretsiz / intraday ücretli)

- **Resmi REST** `GET /futures/data/openInterestHist` (5m…1d, limit≤500):
  **yalnızca son 30 gün** → 2020–2023 backfill İMKANSIZ. (Aynı kısıt
  longShortRatio vb. tüm `/futures/data/*` endpointlerinde.)
- **Vision daily metrics** (`data/futures/um/daily/metrics/BTCUSDT/`):
  günlük OI snapshot'ları mevcut (toplulukça doğrulanmış yol). Günlük
  granularite → 5m/15m/1h sinyaline inmez; rejim bağlamı olarak kullanılabilir.
- **Ücretli intraday:** Tardis `derivative_ticker` (OI+funding+mark/index),
  CoinGlass OI history. Maliyet + lisans + metodoloji notu gerekir.
- **Coverage:** günlük TAM; intraday ücretsiz YOK.
- **Size:** günlük ≈ 1.3k satır (ihmal); intraday 5m ≈ 370k satır (küçük).
- **Timestamp:** REST-poll kaynaklı serilerde (Tardis) local_timestamp vs
  exchange timestamp ayrımı belgelenir; karar anına yuvarlama YUKARI yapılmaz.

## D) Liquidations — CONDITIONAL (ücretli üçüncü parti)

- **Resmi arşiv YOK.** Binance yalnızca canlı `forceOrder` WS (geriye dönük yok).
- **CoinGlass API** (`/api/futures/liquidation/history`, `/aggregated-history`):
  aralık 1m…1w; ince granularite (1m–15m) Standard+ plan; API key zorunlu;
  2019'a uzanan history iddiası (bağımsız doğrulanmalı).
- **Coverage:** sağlayıcıya bağlı; satın almadan ÖNCE 2020-01-01 → 2023-06-30
  5m continuity proof-of-coverage istenmeli (örnek ay çekilip boşluk taraması).
- **Size:** 5m aralık ≈ 370k satır (küçük). CPU küçük.
- **Quality checks:** long+short toplamı vs exchange toplamları (çapraz kontrol),
  sıfır-dolu bloklar (gerçekten sıfır mı, eksik mi?), metodoloji değişim tarihleri,
  revizyon politikası (revize seri kullanılmaz).
- **Legal/repro:** ticari lisans; ham yanıtlar + sürüm notu saklanır; tekrar
  indirilebilirlik garanti değil → reproducibility riski ORTA.

## E) Order book — CONDITIONAL, SUBSET ONLY (ücretli, ağır)

- **Resmi arşiv YOK.**
- **Tardis.dev:** BTCUSDT spot `incremental_book_L2`/trades/quotes
  2019-12-01+; Binance spot 2019-03-30+; top-1000 snapshot + full-depth updates;
  günlük 00:00 UTC re-subscribe (~300–3000ms gap); Binance snapshot'ları
  "generated" (REST'ten). Planlar $350/ay mertebesinden başlar, TB transfer
  limitli, yıllık faturalama koşullarıyla derin arşiv.
- **Boyut gerçeği:** tam L2 replay 2020→2023H1 = TB'lar → "kolayca ekleriz" YOK.
  Feasible subset: `book_ticker` (top-of-book) + `book_snapshot_25` CSV'leri
  5m'ye resample edilir → GB mertebesi, yönetilebilir.
- **Coverage:** spot BTCUSDT TAM (2019-12-01+). Futures book için ayrı plan/
  sembol kontrolü gerekir (bu scout'ta spot varsayıldı; futures-book ayrı iş).
- **Timestamp:** local_timestamp (varış) vs exchange timestamp; 5m bar'a atama
  kuralı: bar close'tan ÖNCEKİ son snapshot (asof-join, asla ileri).
- **Quality:** sequence-gap günleri, re-subscribe gap'leri, generated-snapshot
  günleri işaretlenir; eksik günler doldurulmaz (düşürme politikası).

## F) News / sentiment — NOT FEASIBLE (şimdilik)

- **CryptoPanic:** ücretsiz Developer API 01-04-2026'da kalktı. Growth
  ($50/hafta veya $199/ay): 1-AY history. Enterprise (özel, ~$899/ay+):
  1-YIL history, cursor-pagination, **tarih-aralığı sorgusu yok**.
  → 2020–2023 5m-hizalı backfill pratikte YOK.
- Ek sorunlar: sentiment skor metodolojisi opak; duplicate/syndication;
  survivorship (kapanan kaynaklar); future-article contamination; 5m alpha
  kalıntısı belirsiz; haber-anı slippage çarpanı (config 2x) ayrıca modellenmeli.
- Revisit koşulu: Enterprise arşiv + tarih-aralıklı çekim kanıtlanırsa.

## G) X / social — HOLD (feasibility not edildi, veri eklenmez)

- **Resmi X (2026):** abonelikler kalktı; pay-per-use ($0.005/read, post başına;
  URL'li post $0.200; aylık ~2–3M read cap; ücretsiz tier yok). Full-archive
  self-serve'e açık ama yüksek hacim Enterprise-müzakere gerektirir.
- **Üçüncü parti:** twitterapi.io full-archive search $0.00015/tweet, 2006'ya
  kadar; 100K tweet ≈ $15, 1M ≈ $150.
- **Blokerler:** silinmiş postlar (query-anına göre değişen sonuç → tekrar
  üretilemezlik), retrospektif indeksleme değişimleri, bot/spam, hesap-seçim
  yanlılığı (ön-kayıt şart), 2020–2023 tam-çekim maliyeti ve saklama yükü.
- Görev emri gereği Phase 6'ya X verisi EKLENMEZ; yalnızca bu not düşülür.

## Boyut / compute özeti

| Deney | İndirme | Storage | CPU ek yükü |
|-------|---------|---------|-------------|
| 6A cross-asset | < 500 MB | < 1 GB | < 2 CPU-saat |
| 6B funding | KB'lar | ihmal | ihmal |
| 6C-günlük | KB'lar | ihmal | ihmal |
| 6C-intraday / 6D | MB'lar | < 1 GB | küçük |
| 6E-subset | GB'lar | ~10 GB | orta (resample+rebuild) |
| 6E-full L2 | TB'lar | > 1 TB | BÜYÜK — önerilmez |
| 6F / 6G | — | — | — (feasibility engeli) |
