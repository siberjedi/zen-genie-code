# PHASE 6C — RUN REPORT (revize lock, taze kosu)

**Lock:** M20 6C FINAL + M.20 QC REVIZYONU · **Karar:** FAIL — OI INCREMENTAL EDGE YOK
**CPU:** 0.390 / 12 cpu-sa (6 fit)
**Koruma:** P5(2025H1)/B(2024H1)/C(2024H2)/A(2023H2) DOKUNULMADI.

## Data coverage/hash — MANIFEST_DOWNLOAD_6C.json (sha256 verified, dedup keep-first, ilk-OI gate).
## Integrity — monoton+dup+pozitif assert; grid aidiyet; inf yok.
## Alignment/dedup — ACTUAL-ms asof-backward; T candle R(T) gorur; dedup sonrasi dup STOP (tetiklenmedi).
## Leakage — causality probe PASS, test_phase6c 11/11, NEW = 5 kilitli familya, trailing-only testi.
## Train/validation — FULL n_tr=243728 (gate ≥200k), n_val=51507 (BASE ile esit).
## VAL QC gate — affected UNION = 291/51813 = %0.5616 (union; hucre-toplami DEGIL) per-col={'oi_chg_12': 8, 'oi_z_288': 291, 'oi_price_div': 8, 'oi_chg_1': 5, 'oi_range_288': 291} → PASS (<= %1).
## BASE reproduction — ref=-0.002116745525 got=-0.002116745525 PASS.
## BASE: n_tr=314571 n_val=51798 PSS=-0.002117 edge=-0.706 AUC=0.6811 IC=0.0452 tau=0.156 d=+0.121 power=1.00 q=1.0000
## NEW: n_tr=243746 n_val=51522 PSS=-0.002337 edge=-0.779 AUC=0.6004 IC=0.0245 tau=0.556 d=+0.126 power=1.00 q=1.0000
## FULL: n_tr=243728 n_val=51507 PSS=-0.002174 edge=-0.725 AUC=0.6800 IC=0.0427 tau=0.333 d=+0.122 power=1.00 q=1.0000
## FULL-BASE: DeltaPSS=-0.000016 CI95=[-0.000103,+0.000069] excl0=False
## CI/FDR/effect — gates={'a_fdr': False, 'b_support': True, 'c_econ': False, 'd_effect': False, 'chain': False, 'incremental_ci': False}; exploratory={'L0': {'pss': -0.0026794891203097623, 'edge': -0.8931630401032541, 'rank_ic': 0.0990297700051591, 'n_val': 51507, 'cpu_sec': 158.3}, 'L2': {'pss': -0.002256038856124486, 'edge': -0.7520129520414953, 'rank_ic': -0.00941009780721897, 'n_val': 51507, 'cpu_sec': 836.8}, 'horizon_curve_FULL_L1_scores': {'3': {'n': 51507, 'pss': -0.002796, 'edge': -0.932}, '36': {'n': 51483, 'pss': -0.000427, 'edge': -0.142}, '72': {'n': 51447, 'pss': 0.000823, 'edge': 0.274}}, 'oi_x_regime_descriptive': {'bear_high_vol': {'n': 5807, 'pss': -0.000998, 'edge': -0.333}, 'bear_low_vol': {'n': 10953, 'pss': -0.002743, 'edge': -0.914}, 'bull_high_vol': {'n': 6612, 'pss': -0.002012, 'edge': -0.671}, 'bull_low_vol': {'n': 11052, 'pss': -0.002417, 'edge': -0.806}, 'sideways_high_vol': {'n': 2066, 'pss': -0.002682, 'edge': -0.894}, 'sideways_low_vol': {'n': 15017, 'pss': -0.00266, 'edge': -0.887}}}
## Gates + FINAL: FAIL — OI INCREMENTAL EDGE YOK
## Protected-test verification — TRAIN+VAL loader only; indirme 2020→2023H1 assert'li; holdout verify ALL PASS (kosu sonrasi yeniden kosuldu).
## Revision notu — R-QC (OI<=0 veya non-finite => missing, no fill) + VAL union toleransi <=%1 (M.20 onayli). Onceki STOP kosusu artefaktlari RUN_REPORT_6C_STOPPED.md / MANIFEST_6C_STOPPED.json olarak korunur; bu kosu taze deterministik rerun'dur (devam degil).
## Anomalies — venue sifir-OI glitch bloklari (2021-05-22, 2022-03-07/08, 2023-06-06) manifestte belgeli.
## Exact decision — FAIL — OI INCREMENTAL EDGE YOK
## Union dogrulama — VAL affected union = 291 / 51,825 = %0.5615 (60-dk pencere) ve label-bound pencerede 291 / 51,813 = %0.5616; ikisi de UNION sayimidir (5 feature’in hucre-toplami DEGIL — hucre toplami 603 olurdu). Paydadaki 12 satir farki yalnizca bound tanimindandir; union sayisi (291) aynidir.

**Not:** statistical predictive ≠ economic incremental edge; karar ekonomik incremental edge uzerinden verildi.