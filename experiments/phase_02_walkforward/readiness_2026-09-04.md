# Phase 2 Hazırlık Kontrolü — 2026-09-04

> Phase 2 **çalıştırılmadı**, sadece kontrol. `expanding:false` değiştirilmedi.

## A) Historical Data Downloader
- `scripts/download_data.py:1` `freqtrade download-data --exchange binance --pairs BTC/USDT ETH/USDT --timeframe 5m --days 400`
- `--help` → OK (argparse 4 param)
- `freqtrade` binary host'ta yoksa `FileNotFoundError` → `pip install freqtrade` gerekir (docker içinde var)
- **Durum:** Kod **READY**, veri **NOT READY**

## B) OHLCV Kapsamı (BTC/ETH + TOP30)
- `freqtrade/user_data/data/binance/` → 0 dosya, `data files 0`
- `config/freqtrade.example.json:20` `VolumePairList TOP30 min_value 5M` → 2023-12-31 öncesi 400 gün için BTC/ETH + 28 coin lazım
- **Durum:** **NOT READY** — `make download` veya `python scripts/download_data.py --pairs BTC/USDT ETH/USDT --timeframe 5m --days 400` çalıştırılmalı (Freqtrade docker içinde: `docker exec ai-trader-dryrun freqtrade download-data ...`)

## C) walk_forward.py Fold Üretimi
- `src/backtest/walk_forward.py:7` `WFConfig(train 365, val 90, test 90, step 90, expanding False)` + `generate_folds`
- **Bug:** `config/experiment.yaml:20` `walk_forward.note` alanı `WFConfig(**yaml)`'da `TypeError: unexpected kw 'note'` → filtreleme gerekli (`{k:v for k in fields}`)
- Düzeltme yapılmadı, sadece raporlandı.
- `generate_folds("2020-01-01","2023-12-31")` → 11 fold, gap `-455` (overlap) → **foldlar bağımsız değil**, `overlap_report` zaten var → doğru.
- **Durum:** Kod READY (note filtrelenirse), overlap raporlama READY

## D) WF Config
- `train 365` `validation 90` `test 90` `step 90` `expanding false` → `config/experiment.yaml:18` ile **uyumlu**, değiştirilmedi.
- **Durum:** READY

## E) final_test_A = 2023-07-01 → 2023-12-31 Korunuyor mu?
- `config/experiment.yaml:7` `phase_02_walkforward.final_test_A: 2023-07-01 → 2023-12-31`
- `generate_folds("2020-01-01","2023-12-31")` son 2 fold `test 2023-06-19→2023-09-17` ve `2023-09-17→2023-12-16` → **overlap True** (168 gün iç içe)
- `generate_folds("2020-01-01","2023-06-30")` → 9 fold, son test `2023-06-19` → final_A öncesi, **korunur**
- **Durum:** **NOT READY** eğer default `end 2023-12-31` kullanılırsa final_A sızar. Runner'da guard lazım.

## F) final_test_A Tuning'de Kullanılmayacak mı?
- `walk_forward.py` ve `evaluate.py` `final_test` string'i aramıyor → kod doğrudan kullanmıyor
- Ancak `Makefile:14` `walkforward --end 2023-12-31` → yukarıdaki gibi sızma riski
- **Durum:** Kodda doğrudan kullanım yok (READY), ancak **operasyonel guard** lazım (runner'da eklenecek)

## G) Regime Classifier
- `src/regime/classifier.py:1` `RegimeConfig(sma_fast 50, sma_slow 200, adx_period 14, adx_threshold 20.0, atr_period 14, vol_lookback 30, vol_high 0.70 vol_low 0.30)`
- `classify()` `SMA` `ADX` `ATR` `rank(pct=True)` → `bull/bear/sideways_high_vol/low_vol` birleşik etiket, sadece `t`'ye kadar veri (ta.SMA, rolling rank) → **mekanik, hindsight yok**
- `config/experiment.yaml:24` `regime_classifier.locked true` ile uyumlu
- **Durum:** READY

## H) evaluate.py Yetenekleri
- `src/backtest/evaluate.py:1` artık düzeltildi:
  - `sharpe` `sortino` → günlük `daily_full` +365 (eski per-trade+365 fix)
  - `max_drawdown` → `(1+daily).cumprod()` günlük equity
  - `profit_factor` → `wins/losses`
- `statsmodels.multipletests` `fdr_correct` → Benjamini-Hochberg READY
- `cohens_d` → READY
- `walk_forward.py:18` `overlap_report()` → READY
- `power_target 0.80` (`experiment.yaml:34`) için `statsmodels` power analizi **yok** (evaluate'da hesaplanmıyor) → **partial READY**
- **Durum:** 6/7 READY, power eksik

## Özet
- expanding:false **değişmedi**
- PROTOCOL.md **değişmedi**
- Tarih: 2026-09-04
- Sonuç: Data ve final_A guard **NOT READY**, diğerleri **READY**
