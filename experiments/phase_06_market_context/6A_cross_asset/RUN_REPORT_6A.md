# PHASE 6A — RUN REPORT

**Lock:** M20 6A FINAL · **Karar:** FAIL — CROSS-ASSET INCREMENTAL EDGE YOK
**CPU:** 0.762 / 12 cpu-sa (12 fit)
**Koruma:** P5(2025H1)/B(2024H1)/C(2024H2)/A(2023H2) DOKUNULMADI.

## 1. Lock ID / commit — M20 6A FINAL (dosya lock, commit yok)
## 2/3. Data hashes / coverage — MANIFEST_DOWNLOAD_6A.json (294 dosya, sha256 verified) + data/xa_features.parquet; 7/7 sembol 367314 bar, BTC grid drop 0.
## 4. Integrity checks — monoton+dup+pozitif (indiricide assert), grid eslesme assert, inf yok.
## 5. Leakage checks — causality probe PASS, test_phase6a 12/12, NEW-kolon = 6 kilitli familya (blok kolonu yok), trailing-only formul testi.
## 6. BASE reproduction — E032 PSS ref=-0.002116745525, got=-0.002116745525 (tol 1e-9, PASS).
## BASE: n_tr=314571 n_val=51798 PSS=-0.002117 edge=-0.706 AUC=0.6811 IC=0.0452 tau=0.156 d=+0.121 power=1.00 q=1.0000
## NEW: n_tr=314611 n_val=51813 PSS=-0.002252 edge=-0.751 AUC=0.6206 IC=0.0384 tau=0.511 d=+0.116 power=1.00 q=1.0000
## FULL: n_tr=314571 n_val=51798 PSS=-0.002159 edge=-0.720 AUC=0.6800 IC=0.0455 tau=0.289 d=+0.120 power=1.00 q=1.0000
## 10. FULL-BASE: DeltaPSS=-0.000038 CI95=[-0.000103,+0.000029] excl0=False
## 11/12/13. CI/FDR/effect — FDR q: BASE/NEW/FULL; gates={'a_fdr': False, 'b_support': True, 'c_econ': False, 'd_effect': False, 'chain': False, 'incremental_ci': False}; exploratory={'L0': {'pss': -0.0028443907283301016, 'edge': -0.9481302427767005, 'rank_ic': 0.09944807517251389, 'n_val': 51798, 'cpu_sec': 188.0}, 'L2': {'pss': -0.0024129646038448596, 'edge': -0.8043215346149531, 'rank_ic': -0.0017150635475940818, 'n_val': 51798, 'cpu_sec': 1114.6}, 'horizon_curve_FULL_L1_scores': {'3': {'n': 51798, 'pss': -0.002772, 'edge': -0.924}, '36': {'n': 51774, 'pss': -0.000324, 'edge': -0.108}, '72': {'n': 51738, 'pss': 0.001049, 'edge': 0.35}}, 'loo': {'BNBUSDT': {'pss': -0.002151, 'edge': -0.717, 'n_val': 51798, 'cpu_sec': 176.0}, 'XRPUSDT': {'pss': -0.002129, 'edge': -0.71, 'n_val': 51798, 'cpu_sec': 164.5}, 'ADAUSDT': {'pss': -0.002106, 'edge': -0.702, 'n_val': 51798, 'cpu_sec': 165.6}, 'DOGEUSDT': {'pss': -0.002136, 'edge': -0.712, 'n_val': 51798, 'cpu_sec': 164.3}, 'LTCUSDT': {'pss': -0.002162, 'edge': -0.721, 'n_val': 51798, 'cpu_sec': 164.4}, 'BCHUSDT': {'pss': -0.002121, 'edge': -0.707, 'n_val': 51798, 'cpu_sec': 164.5}, 'ETHUSDT': {'note': 'dusurulmedi (F5 numeraire kilitli)'}}}
## 14/15. Gates + FINAL: FAIL — CROSS-ASSET INCREMENTAL EDGE YOK
## 16. Protected-test verification — loader TRAIN+VAL only; 2023-07+ URL uretilmedi (assert); holdout verify ALL PASS (verify_2025H1.json, kosu sonrasi yeniden kosuldu).
## 17. Anomalies — yok (varsa buraya).
## 18. Exact decision — FAIL — CROSS-ASSET INCREMENTAL EDGE YOK

**Not:** statistical predictive (AUC/IC) ≠ economic incremental edge; karar ekonomik incremental edge uzerinden verildi.