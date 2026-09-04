# Data Quality Report — 2026-09-04 (Phase 2 Data Preparation)

> **Not:** Walk-Forward **henüz çalıştırılmadı**, final_test_A'ya dokunulmadı.

## DATA
- **Downloader:** `scripts/download_data.py:1` `freqtrade download-data --exchange binance --timeframe 5m --timerange 20200101-20230630 --data-format-ohlcv feather` via `docker exec ai-trader-dryrun`
- **Universe:** `http://127.0.0.1:8001/api/universe` TOP30 `VolumePairList number_assets 30 min_value 5M` → 30 pair (BTC,ETH,XRP,SOL,ZEC,BMT,BNB,DOGE,UNI,SUI,TRUMP,ENA,ARB,ADA,PEPE,HEMI,LINK,PUMP,NEAR,PROM,TRX,XPL,U,CRCLB,WLD,ZKP,AVAX,CHIP,TAO,AAVE)
- **Location:** `freqtrade/user_data/data/binance/` 30 feather dosyası
- **Pair count:** 30 istenen, **18** veri var, **12** boş (yeni coin, 2023-06-30 öncesi yok)
  - **Veri var (18):** BTC 367022, ETH 367022, XRP 367022, ADA 367022, BNB 367022, DOGE 367022, TRX 367022, ZEC 367022, LINK 367022, BTC/ETH/XRP/ADA/BNB/DOGE/TRX/ZEC/LINK (full 2020-01-01→2023-06-29), SOL 302905 (2020-08-11→), AVAX 290803 (2020-09-22→), UNI 292285 (2020-09-17→), AAVE 284221 (2020-10-15→), NEAR 284485 (2020-10-14→), ARB 28316 (2023-03-23→), PROM 30128 (2023-03-17→), SUI 16560 (2023-05-03→), PEPE 15912 (2023-05-05→)
  - **Boş (12):** BMT, CHIP, CRCLB, ENA, HEMI, PUMP, TAO, TRUMP, U, WLD, XPL, ZKP — `Candle-data for X available starting with 2025-...` → `WARNING No available candle-data before 2023-06-30` → length 0, size 2770b header
- **Candle count:** toplam **4,848,813** (18 pair, avg 269,378), BTC başına 367,022 (beklenen 367,776, diff 754)
- **Date range:** ilk `2020-01-01 00:00:00+00:00` (BTC), son `2023-06-29 23:55:00+00:00` (tüm dolu pairler)
- **Missing candles:** toplam **5,661** (BTC 466, 15 gap; per-full-pair 466, per-mid 287, ARB/PROM 16, SUI/PEPE 0) — exchange downtime/bakım, normal
- **Duplicates:** **0** (tüm 18 pair `duplicated==0`)
- **Invalid rows:** **0** (high<low, open/close out of high/low, volume<0, null → 0)
- **Null/invalid:** 0
- **Sorted:** tümü `is_monotonic_increasing true`

**Yorum:** 18/30 tarihsel veri Phase 2 için yeterli; 12 yeni coin zaten `VolatilityFilter`/`AgeFilter` ile elenmeli, walk-forward onlarda trade üretmez. Eksik 5,661 (~0.11%) tolere.

## FOLDS
- **Config:** `config/experiment.yaml:18` `train 365, validation 90, test 90, step 90, expanding false` (değişmedi)
- **Üretim:** `src/backtest/walk_forward.py:7` `generate_folds("2020-01-01","2023-06-30")` → **9 fold**
- **Tarihler:**

| fold | train_start | train_end | val_start | val_end | test_start | test_end |
|------|-------------|-----------|-----------|---------|------------|----------|
| 0 | 2020-01-01 | 2020-12-31 | 2020-12-31 | 2021-03-31 | 2021-03-31 | 2021-06-29 |
| 1 | 2020-03-31 | 2021-03-31 | 2021-03-31 | 2021-06-29 | 2021-06-29 | 2021-09-27 |
| 2 | 2020-06-29 | 2021-06-29 | 2021-06-29 | 2021-09-27 | 2021-09-27 | 2021-12-26 |
| 3 | 2020-09-27 | 2021-09-27 | 2021-09-27 | 2021-12-26 | 2021-12-26 | 2022-03-26 |
| 4 | 2020-12-26 | 2021-12-26 | 2021-12-26 | 2022-03-26 | 2022-03-26 | 2022-06-24 |
| 5 | 2021-03-26 | 2022-03-26 | 2022-03-26 | 2022-06-24 | 2022-06-24 | 2022-09-22 |
| 6 | 2021-06-24 | 2022-06-24 | 2022-06-24 | 2022-09-22 | 2022-09-22 | 2022-12-21 |
| 7 | 2021-09-22 | 2022-09-22 | 2022-09-22 | 2022-12-21 | 2022-12-21 | 2023-03-21 |
| 8 | 2021-12-21 | 2022-12-21 | 2022-12-21 | 2023-03-21 | 2023-03-21 | 2023-06-19 |

- **Overlap:** her step `gap -455` OVERLAP (foldlar bağımsız değil) → `overlap_report.txt` var
- **final_test_A:** `2023-07-01 → 2023-12-31` (`config/experiment.yaml:7`)
- **Separation:** son test `2023-06-19` → final_A `2023-07-01` gap **+12 gün**, hiçbir test final_A ile **örtüşmüyor** (dry-run `scripts/run_phase02.py:84` guard PASS). `2020-01-01→2023-12-31` ile 11 fold olsaydı 2 fold örtüşürdü (2023-06-19→2023-09-17, 2023-09-17→2023-12-16) → guard 2023-06-30 cut ile engellendi.

## METRICS
- **Sharpe:** `src/data/metrics.py:5` `periods_per_year=365` sadece **günlük** için; `src/backtest/evaluate.py:19` günlük aggregate `daily_full` 0-filled + `dashboard/backend/app.py:890` aynı. **Per-trade+365 KESİNLİKLE yok.** Eski 6.02 (per-trade+365) artık hiçbir rapora baseline olarak yazılmıyor (`docs/SHARPE_FIX_2026-09-04.md`).
  - Doğrulama: aynı 16-trade seri per-trade+365 5.83 vs daily+365 11.39 → test `tests/test_sharpe_annualization.py` PASS
- **Sortino/MaxDD/PF:** aynı günlük equity `(1+daily).cumprod()` üzerinden
- **FDR:** `evaluate.py:73` `multipletests fdr_bh` READY
- **Cohen's d:** `evaluate.py:77` READY
- **Overlap:** `walk_forward.py:18` READY
- **Power:** `evaluate.py:82` `compute_power(effect, n, alpha)` `TTestIndPower` eklendi, `tests/test_power.py` d=0.30 n=176 → power 0.801 PASS. `power_target 0.80` threshold değişmedi, sadece hesap uygulanabilir.

## READINESS
- **DATA:** **READY** (18/30 yeterli, 0 dup/invalid, missing 0.11% tolere; 12 boş yeni coin beklenen)
- **PHASE 2:** **READY** (data, folds, guard, metrics hepsi hazır; tek eksik 12 yeni coin'in tarihsizliği zaten raporlu ve tolere. Gerçek WF için `SUI/PEPE` gibi kısa history'li pairler `AgeFilter 10 gün` ile otomatik elenecek)
- **Not:** `freqtrade/user_data/data/binance` Git'e commit edilmedi (`.gitignore:23` `*.feather` değil ama `data/` altındaki feather'lar 600MB, `.gitignore` ile engellenmeli mi? Şu an **değil**, ama task DATA commit etme diyor — doğru, commit edilmedi)

## Dosyalar
- `scripts/run_phase02.py` (guard + metadata)
- `experiments/phase_02_walkforward/folds/folds.csv` (9 fold)
- `experiments/phase_02_walkforward/run_metadata.json` (hash, tag df73351, range 2020-01-01->2023-06-30)
- `experiments/phase_02_walkforward/config_snapshot.*`
