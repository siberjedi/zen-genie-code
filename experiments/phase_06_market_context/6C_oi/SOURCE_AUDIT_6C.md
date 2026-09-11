# SOURCE AUDIT 6C — Open Interest kaynakları (2026-09-08 taraması)

## S1) Binance Vision `data/futures/um/daily/metrics/BTCUSDT/` — BİRİNCİL ADAY
- İçerik: `create_time, symbol, sum_open_interest, sum_open_interest_value,
  count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio,
  count_long_short_ratio, sum_taker_long_short_vol_ratio` (+türev alanlar).
- **Kritik bulgu:** dosyalar "daily" adını taşısa da snapshot'lar **5m
  kadanslıdır** (dokümante kullanıcı kanıtı + üçüncü-parti ayna:
  `create_time_ms`, 5m OI + long/short oranları).
- Kapsama (ayna kanıtı): OI **2020-09-10'dan itibaren tam dolu**; oran
  kolonlarında 2022-Q1 civarı küçük boşluklar (taker_ls ~128 gün, ls_count ~19
  gün — OI sütunları etkilenmiyor).
- Ücretsiz, keyless, checksum'lu resmi arşiv.

## S2) Binance REST `/futures/data/openInterestHist` — ELENDİ (arşiv için)
- 5m…1d periyotlar, limit≤500, **yalnızca son 30 gün**. 2020–2023 backfill
  imkansız. (Tüm `/futures/data/*` ailesinde aynı kısıt.)

## S3) Binance REST `/fapi/v1/openInterest` — ELENDİ (arşiv için)
- Yalnızca güncel snapshot. Tarihçe yok; geriye dönük çalışmada yeri yok.
  (Canlı polling ile yeni tarihçe biriktirilebilir — locked pencereye faydası yok.)

## S4) CoinGlass OI History OHLC — YEDEK (ücretli)
- `/api/futures/open-interest/history`: BTCUSDT/Binance, 1m…1w aralıklar,
  OHLC format, limit 1000/sayfa, API key zorunlu.
- İnce granularite (1m–15m) Standard+ plan; Hobbyist ≥4h, Startup ≥30m.
- Tarih derinliği OI-özelinde belgelenmemiş (genel "2019+" pazarlama iddiası);
  satın almadan önce proof-of-coverage şart. Revizyon politikası belirsiz.

## S5) Tardis `derivative_ticker` — YEDEK (ücretli)
- OI+funding+mark/index; Binance OI WS olmadığı için **REST-poll fallback**
  (dakika-mertebe poll damgası; tick değil). 2019+ kapsama iddialı, planlı erişim.

## S6) HF aynası (ibrahimdaud/binance-btcusdt) — REFERANS ONLY
- Vision metrics'in üçüncü-parti aynası (2020-09-10 → 2026-05-31, 5m OI tam,
  oranlarda küçük boşluklar). Birincil kaynak OLAMAZ (üçüncü-parti,
  revizyon/durabilirlik riski); yalnızca S1 iddialarını destekleyen çapraz kanıt.

## New-information hükmü (scout ile aynı)
OI değişimi / z-score / price-OI divergence = YES (OHLCV'de yok). Bu dosyada
karar yalnızca **test edilebilirlik** hakkındadır.
