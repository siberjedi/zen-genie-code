# PHASE 6B — RUN REPORT

**Lock:** M20 6B FINAL · **Karar:** FAIL — FUNDING INCREMENTAL EDGE YOK
**CPU:** 0.443 / 12 cpu-sa (6 fit)
**Koruma:** P5(2025H1)/B(2024H1)/C(2024H2)/A(2023H2) DOKUNULMADI.

## Veri coverage/hash — MANIFEST_DOWNLOAD_6B.json: 3831 settlement, 2020-01-01 00:00 → 2023-06-30 16:00, max jitter 0.047s, eksik yok; markPrice EXCLUDED.
## Integrity — monoton+dup+NaN yok; grid aidiyet ±60s; aralik 8h±60s.
## Settlement alignment — ACTUAL ms asof-backward; T candle R(T) gorur, oncesi gormez (test 12/12).
## Leakage — causality+predicted probe PASS; NEW = 5 kilitli familya; trailing-only formul testi.
## BASE reproduction — ref=-0.002116745525 got=-0.002116745525 PASS.
## BASE: n_tr=314571 n_val=51798 PSS=-0.002117 edge=-0.706 AUC=0.6811 IC=0.0452 tau=0.156 d=+0.121 power=1.00 q=1.0000
## NEW: n_tr=306163 n_val=51813 PSS=-0.003023 edge=-1.008 AUC=0.5362 IC=0.0014 tau=-0.200 d=-0.069 power=0.94 q=1.0000
## FULL: n_tr=306145 n_val=51798 PSS=-0.002164 edge=-0.721 AUC=0.6798 IC=0.0453 tau=0.244 d=+0.116 power=1.00 q=1.0000
## FULL-BASE: DeltaPSS=-0.000037 CI95=[-0.000107,+0.000033] excl0=False
## CI/FDR/effect — gates={'a_fdr': False, 'b_support': True, 'c_econ': False, 'd_effect': False, 'chain': False, 'incremental_ci': False}; exploratory={'L0': {'pss': -0.0028153505915166676, 'edge': -0.9384501971722226, 'rank_ic': 0.09991330891908193, 'n_val': 51798, 'cpu_sec': 178.6}, 'L2': {'pss': -0.0024441002370949546, 'edge': -0.8147000790316515, 'rank_ic': 0.005353491044370996, 'n_val': 51798, 'cpu_sec': 1033.5}, 'horizon_curve_FULL_L1_scores': {'3': {'n': 51798, 'pss': -0.002784, 'edge': -0.928}, '36': {'n': 51774, 'pss': -0.000404, 'edge': -0.135}, '72': {'n': 51738, 'pss': 0.000961, 'edge': 0.32}}, 'funding_x_regime_descriptive': {'bear_high_vol': {'n': 5857, 'pss': -0.001514, 'edge': -0.505}, 'bear_low_vol': {'n': 10976, 'pss': -0.00261, 'edge': -0.87}, 'bull_high_vol': {'n': 6663, 'pss': -0.001845, 'edge': -0.615}, 'bull_low_vol': {'n': 11170, 'pss': -0.002197, 'edge': -0.732}, 'sideways_high_vol': {'n': 2068, 'pss': -0.002514, 'edge': -0.838}, 'sideways_low_vol': {'n': 15064, 'pss': -0.002718, 'edge': -0.906}}, 'settlement_window_sensitivity': {'within_1h': {'n': 13139, 'pss': -0.002267, 'edge': -0.756}, 'outside_1h': {'n': 38659, 'pss': -0.002109, 'edge': -0.703}}}
## Gates + FINAL: FAIL — FUNDING INCREMENTAL EDGE YOK
## Protected-test verification — TRAIN+VAL loader only; istek penceresi 2020→2023H1 assert'li; holdout verify ALL PASS (kosu sonrasi yeniden kosuldu).
## Anomalies — jitter disambiguation (RUN_REPORT notu): 2 settlementte ms-mertebe jitter (maks 47ms); actual-ms asof ile sizinti yok.
## Exact decision — FAIL — FUNDING INCREMENTAL EDGE YOK

**Not:** statistical predictive ≠ economic incremental edge; karar ekonomik incremental edge uzerinden verildi.