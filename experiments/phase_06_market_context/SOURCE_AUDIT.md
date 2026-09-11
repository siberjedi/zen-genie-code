# SOURCE AUDIT — 7 bağımsız aday (incremental-information merceği)

Her aday: NEW INFORMATION? (YES / PARTIAL / NO / UNCERTAIN) + gerekçe.
"Model denemedik; bu tablo sonuçlara göre değil, bilgi-içeriği analizine göre."

## A) CROSS-ASSET / MARKET CONTEXT

| Alt-aday | New info? | Gerekçe |
|----------|-----------|---------|
| BTC 5m return momentum (kendi serisinden) | NO | B0'da ret_1..ret_72 olarak zaten var |
| BTC cross-sectional rank (tek sembol) | NO | Tek sembolde rank tanımsız |
| ETH/BTC, majör parite ilişkisi (ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT…) | PARTIAL | BTC serisinden türetilemez; ama BTC ile korelasyon yüksek → redundancy riski |
| Market-wide breadth (% yükselen majör) | YES (zayıf-güçlü arası) | Tekil BTC OHLCV'de yok; sistemik risk-on/off bilgisi taşır |
| Aggregate market return (cap-ağırlıklı) | PARTIAL | BTC zaten marketin ~%50'si; BTC return'e yakın |
| Dispersion (majörler arası getiri yayılımı) | YES | Volatilite-rejim bilgisi; ATR/roll_std'den farklı kaynak |
| Correlation regime (BTC vs majörler, rolling) | YES | Bağlılık rejimi; OHLCV'de karşılığı yok |
| BTC dominance | PARTIAL | Türetilebilir proxy'ler var ama doğrudan seri yeni |

**Hüküm:** Kısmen incremental. Breadth/dispersion/correlation-regime YES;
tek-parite returnleri PARTIAL (redundancy test edilmeli — ablation ile).

## B) FUNDING

| Alt-aday | New info? | Gerekçe |
|----------|-----------|---------|
| BTCUSDT perp funding rate (settled, 8h) | YES | Spot OHLCV'de yok; kaldıraçlı pozisyonlanma baskısını ölçer |
| Funding z-score / percentile | YES | Aynı — türetilmiş ama kaynağı yeni |
| Funding × price divergence | YES | İki kaynağın etkileşimi; OHLCV-tekilinde yok |
| Predicted (intraperiod) funding | UNCERTAIN | Mark/index'ten tahmin edilebilir → kısmen türetilebilir; ayrıca metodoloji riski |

**Hüküm:** YES. En temiz incremental kaynaklardan biri. Uyarı: 8h kadans →
5m horizon'da zayıf, 1h/rejim kullanımında güçlü.

## C) OPEN INTEREST

| Alt-aday | New info? | Gerekçe |
|----------|-----------|---------|
| OI değişimi (intraday) | YES | OHLCV'de yok; pozisyon akışı bilgisi |
| OI z-score | YES | Aynı |
| Price/OI divergence | YES | İki kaynak etkileşimi |
| Günlük OI (Vision metrics) | PARTIAL | Rejim bağlamı verir ama 5m/15m sinyaline inmez |

**Hüküm:** YES (bilgi olarak) — AMA intraday arşiv ücretsiz yok. Bilgi-değeri
yüksek, erişim-değeri orta.

## D) LIQUIDATIONS

| Alt-aday | New info? | Gerekçe |
|----------|-----------|---------|
| Long/short liquidation imbalance | YES | OHLCV'de yok; zorunlu akış (cascades) bilgisi |
| Liquidation burst (rejim filtresi) | YES | Nadir-olay göstergesi |
| Liquidation/volume ratio | PARTIAL | Volume zaten var; oran yeni ama payda tanıdık |

**Hüküm:** YES (bilgi olarak) — AMA yalnızca üçüncü-parti arşiv; metodoloji/
revizyon riski ve burst-doğası (5m'de seyrek) nedeniyle dikkat.

## E) ORDER BOOK / MICROSTRUCTURE

| Alt-aday | New info? | Gerekçe |
|----------|-----------|---------|
| Bid/ask imbalance (top-of-book) | YES | Trade-gerçekleşmiş OHLCV'de yok (quote bilgisi) |
| Spread | PARTIAL | Volatilite ile korelasyonlu ama mikro-yapısal; kısmen yeni |
| Depth imbalance (top-N) | YES | Likidite duvarı bilgisi |
| Full-depth L2 replay | YES (teknik) | Bilgi var ama TB-maliyet → pratikte NO |

**Hüküm:** Top-of-book YES; full-depth pratikte NO (maliyet). Tardis
book_ticker/book_snapshot_25 subset'i ile test edilebilirlik var.

## F) NEWS / SENTIMENT

| Alt-aday | New info? | Gerekçe |
|----------|-----------|---------|
| Timestamped crypto haber akışı | UNCERTAIN | Fiyat çoğu haberi dakikalar içinde sindirir; 5m'de alpha kalıntısı belirsiz |
| Sentiment skoru (sağlayıcı) | UNCERTAIN | Skor metodolojisi opak; ground-truth yok; sağlayıcıya bağımlı |
| PanicScore/dikkat metriği | PARTIAL | Hacim/volatilite ile korelasyonlu olabilir → redundancy şüphesi |

**Hüküm:** Bilgi-değeri UNCERTAIN + erişim-değeri LOW (arşiv yok) → REJECT (şimdilik).

## G) X / SOCIAL

| Alt-aday | New info? | Gerekçe |
|----------|-----------|---------|
| Post hacmi/duygu (aggregate counts) | UNCERTAIN | Haberle aynı sindirim sorunu + bot/spam |
| Kanaat önderi akışı | UNCERTAIN | Seçim yanlılığı (hangi hesap? neden?) — ön-kayıt gerekir |
| Silinmiş-post düzeltmeli seri | NO (pratikte) | Survivorship düzeltmesi geriye dönük yapılamaz |

**Hüküm:** UNCERTAIN + HOLD (görev emri: Phase 6'ya doğrudan ekleme).
