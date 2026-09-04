# Phase 2 Sanity Check — 2026-09-04 (strategy/protocol UNCHANGED)

> Amaç: Baseline gerçekten kötü mü, pipeline hatası mı? Eski sonuç OVERWRITE EDİLMEDİ (`metrics.csv`, `RESULT_2026-09-04.md` duruyor). Düzeltmeler ayrı versiyon (`metrics_v2.csv`, bu dosya).

## 1) Freqtrade Cross-Check (9 fold, StaticPairList 18, fee 0.001, 5m, Baseline dondurulmuş)
| fold | FT trades | OUR trades | FT profit_abs | OUR net | FT WR | OUR WR | FT PF | OUR PF_old | PF_new | FT DD | OUR DD_old | DD_new |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 455 | 455 | -33.955 | -33.955 | 0.7253 | 0.7253 | 0.869 | 0.855 | 0.869 | 0.5933 | -0.9602 | -0.5844 |
| 1 | 395 | 395 | +5.637 | +5.637 | 0.7038 | 0.7038 | 1.038 | 1.070 | 1.038 | 0.1807 | -0.4811 | -0.1778 |
| 2 | 387 | 387 | -30.476 | -30.476 | 0.6434 | 0.6434 | 0.750 | 0.780 | 0.750 | 0.3605 | -0.8039 | -0.3570 |
| 3 | 391 | 391 | -26.651 | -26.651 | 0.6496 | 0.6496 | 0.773 | 0.811 | 0.773 | 0.3607 | -0.7982 | -0.3547 |
| 4 | 384 | 384 | -44.487 | -44.487 | 0.6432 | 0.6432 | 0.657 | 0.685 | 0.657 | 0.5052 | -0.9017 | -0.4987 |
| 5 | 381 | 381 | -12.869 | -12.869 | 0.6745 | 0.6745 | 0.889 | 0.918 | 0.889 | 0.2094 | -0.5591 | -0.1904 |
| 6 | 349 | 349 | -27.301 | -27.301 | 0.6132 | 0.6132 | 0.726 | 0.741 | 0.726 | 0.3014 | -0.7033 | -0.2914 |
| 7 | 350 | 350 | -7.829 | -7.829 | 0.6257 | 0.6257 | 0.907 | 0.920 | 0.907 | 0.1643 | -0.4017 | -0.1462 |
| 8 | 362 | 362 | -33.454 | -33.454 | 0.6243 | 0.6243 | 0.661 | 0.648 | 0.661 | 0.3776 | -0.8322 | -0.3758 |

- trade count / P&L / WR: **exact match 9/9** (pipeline doğru okuyor)
- PF: old ratio ~0.02-0.03 sapma (stake değişken 16.4-51.3, mean 30.5). **New abs FT ile exact match 9/9.** Hata: `profit_factor(profit_ratio)` yerine `profit_abs` olmalıydı (stake sabit değil).
- DD: old ratio-cumprod **abartı** (-0.96 vs 0.59). **New wallet-simple FT ile ±0.01.** Hata: `(1+daily_ratio_sum).cumprod()` stake!=wallet olduğu için abartıyor.
- Sharpe: our daily -1.647 vs FT wallet -1.748 (fold0), diff 0.1. FT `sharpe` -4.66 closed-trades (farklı tanım). Primary daily TRUSTED.
- **Verdict cross-check: TRADE/P&L PASS, PF/DD FIXED in v2, Sharpe PASS.**

## 2) Equity / MaxDD kaynağı
- Aggregate -100% (`run_metadata.json: aggregate.max_dd -0.99999`, equity 1.0->0.000035) **iki katmanlı hata**:
  1. Metod: `(1+daily_ratio_sum).cumprod()` wallet değil (yukarıda).
  2. Aggregation: 9 fold her biri fresh 100 start. Günlük abs toplam -211.38. Sürekli portföy varsayımı 100-211=-111 (negatif, imkansız). Testler contiguous (2021-03-31->2023-06-19) ama her backtest fresh 100, compounding taşınmıyor.
- Doğru yorum: **9 bağımsız 100-start run, ort -23.48/fold, worst -44.49 (fold4), best +5.64 (fold1).** Per-fold wallet DD: FT 59%,18%,36%,36%,50%,20%,30%,16%,37% (ort ~33%). Aggregate ruin YOK.
- Fix: `metrics_v2.csv: max_dd_new_wallet` (100+cum daily_abs). Test: `tests/test_maxdd.py` PASS (wrong -30% vs correct -9.9%).
- Eski `metrics.csv:max_dd` ve `run_metadata aggregate.max_dd` OVERWRITE EDİLMEDİ, v2 ayrı.

## 3) Trade P&L ayrımı (3454 trade)
- gross_w **+962.15**, gross_l **-1173.53**, net **-211.38** (`trades.csv` profit_abs sum).
- Fee: `fee_open=fee_close=0.001` unique. Örnek ETH fold0: open 32.9656, close 33.1877, fee_est 0.0662, gross 0.2221, net 0.1560 == profit_abs 0.1560 **exact**. Fee entry+exit birer kez, **double-count YOK**. Toplam fee_est ~211.24 (volume 105618.7*0.002).
- Slippage: freqtrade backtest slippage model YOK (0). Varsayım 5bps uygulanmadı (Madde 12). **Slippage 0, fee dahil.**
- Net P&L fee-dahil, slippage-haric.

## 4) ROI / SL / Signal (991/178/2265 doğrulandı)
- `trades.csv` exit_reason: **exit_signal 2265, roi 991, stop_loss 178, force_exit 20 = 3454 exact.**
- Baseline ROI 2%, SL -10%, exit RSI>70 ile tutarlı: 991 ROI (%2 win), 178 SL (%-10 loss), 2265 signal (çoğunluk), 20 force_exit (test sonu açık).
- Fold0 detayı: roi 244, signal 154, SL 54 (2021 Q2 bull, ROI fazla) — overall signal ağırlıklı.

## 5) Sharpe (daily aggregate, 0-filled, 365)
- Yöntem: `profit_ratio` sum per day, takvim 2021-03-31->2023-06-18 (810 gün), 0-filled. `src/backtest/evaluate.py:19`, `dashboard/app.py:890` aynı. Per-trade+365 YOK.
- daily_full len 810, nonzero 794, zero 16 (trade'siz gün = 0 return, doğru).
- **daily aggregate Sharpe -1.807**, nonzero-only -1.825 (fark 0.018, 0-filled etkisi ihmal).
- wallet (abs/100) Sharpe -1.799 (fark 0.008, scaling cancels). **Primary TRUSTED.**
- fold median -1.684, mean -1.746 (metrics.csv). FT wallet Sharpe ile diff 0.1-0.3 (kabul).
- Eski 6.02 hiçbir yeni rapora baseline yazılmadı.

## 6) Universe per-fold
- Eligible 18, excluded 12 (tarihsiz). Folds 0-7: **14 pair** (ARB/PROM/SUI/PEPE henüz yok, 2023-03+), fold8: **18 pair**.
- ARB 8, PEPE 5, SUI 12, PROM 31 trade (sadece fold8). Diğer 14 pair tüm foldlarda.
- Otomatik elenme raporlandı, zorla dahil YOK.

## 7) Leakage
- Max close **2023-06-19 00:00:00+00:00**, final_A start 2023-07-01. **0 trade >=2023-07-01.** Min open 2021-03-31.
- Guard `scripts/phase02_analyze.py:84` PASS. **Touched NO.**

## 8) Değişiklik yok
- BaselineStrategy, PROTOCOL.md, experiment thresholds, Final Test A, FreqAI: **dokunulmadı** (`git diff df73351..HEAD -- PROTOCOL.md config/experiment.yaml ...` boş).
- Fixler: `metrics_v2.csv` (yeni), `tests/test_maxdd.py` (yeni), bu dosya (yeni). Eski `metrics.csv`/`RESULT_2026-09-04.md` duruyor.

## Verdict
- Phase 2 trade/P&L/Sharpe/regime/leakage **TRUSTED** (FT ile exact match).
- MaxDD/PF evaluator hatası **FIXED in v2** (FT ile match). Aggregate -100% ve -211 sürekli-portföy olarak YORUMLANAMAZ (9x100 bağımsız).
- Baseline OOS edge: **YOK** (düzeltilmiş DD ort ~33%, Sharpe -1.8, PF 0.82, win %65 ama expectancy negatif). Sonuç kötü, pipeline değil.
