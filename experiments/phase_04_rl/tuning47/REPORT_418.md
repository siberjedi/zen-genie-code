
## 1. Executive Summary

- A) **Decision-level predictive edge: DECISION-LEVEL EDGE YOK**
- B) Economic trading edge: BU FAZIN resmi sonucu DEĞİL; 4.17 locked A-gate E1 icin FAIL idi (mean 0.225 < 0.80).
- C) RL ≈ exposure × market drift: 4.16/4.17 bu yonde idi; 4.18 karar-duzeyi bulgusu da ayri seed'larda kontrol-medyaninin altında (C1/C3 fail) → drift-diskirimi korunuyor.
- Flow: leakage audit **PASS** (7 kontrol) → events → forward (2000 MC/seed) → stats → decomp → rapor.
- Verdict (prereg C1..C4): **edge YOK**: C1 lower-CI>0 fail (pooled BUY h12), C3 >=3/5 seed ayni yonde fail ({'min_q': 0.0033, 'directed_seeds': 1, 'n_signal_seeds': 4}), C2 q<0.05 (123 ama LOW POWER+asimetrik), C4 sanity PASS.

## 2. Research Question

RL policy, giris kararini verdigi ANDA gelecekteki getiriyi ongoren bilgi tasiyor mu? (decision-level predictive power; P&L/Sharpe degil)

## 3. Preregistered Hypothesis

- H0: RL BUY sonrasi h=1h forward getirisi, rejim-stratifiye random/control girislerinden AYRISMaz (median fark 0, dir-acc 0.5).
- H1: Pozitif ayrisma var (gercek sinyal). Ikincil H1: SELL sonrasi negatif ayrisma.

## 4. Dataset

- BTC/USDT 5m val `2023-01-01..2023-06-30`; len(closes)=51825, n_tradable=51794, off=30.
- Seeds: {SEEDS}; Kaynak: `art_E1_seed{s}.json` (action dizileri) + prices; FreqAI satiri phase03 val_trades ile.
- Cikti artefacts: events/forward/stats/decomp418.json

## 5. Leakage Audit

- [OK] semantics: action k <-> candle 30+k (tail +1 = forced-close) — len(closes)=51825 == len(actions)+31=51825 (actions span candles 30..51823)
- [OK] n_tradable convention — 51794 == 51794
- [OK] obs window ends before execution candle — max(obs idx) = 30+k-1 < 30+k (structural, always true)
- [OK] execution candle not in forward window — r_h uses close[30+k+h]/close[30+k], h>=1 -> base index only, so candle 30+k never counted as future
- [OK] forward base == execution candle — base index == 30+k for every event (checked in code path)
- [OK] train-only normalizer preserved — normalizer NOT fit/applied here; actions read from saved post-training artifacts only
- [OK] replay equity == saved equity (all seeds) — {'42': True, '7': True, '123': True, '2026': True, '999': True}
- Replay-equality: {'42': {'seed': 42, 'recon': 137.503715, 'saved': 137.503715, 'delta': -0.0, 'ok': True}, '7': {'seed': 7, 'recon': 97.277749, 'saved': 97.277749, 'delta': 0.0, 'ok': True}, '123': {'seed': 123, 'recon': 118.750918, 'saved': 118.750918, 'delta': -0.0, 'ok': True}, '2026': {'seed': 2026, 'recon': 100.0, 'saved': 100.0, 'delta': 0.0, 'ok': True}, '999': {'seed': 999, 'recon': 180.799818, 'saved': 180.799818, 'delta': 0.0, 'ok': True}}
- Kilit semantik: `obs=closes[k:k+30]`, `execution=close[30+k]`, `r_h=close[30+k+h]/close[30+k]-1` (execution candle forward aralikta YOK, h>=1). Feature'lar obs pencere disina cikmaz; normalizer train-only (burada fit/apply yok); action dizileri post-training sabit kayitlar.

## 6. BUY Results (RL buy forward-return vs random/control)

| seed | n | rl_mean | rl_med | ctrl_med-med | mc_p(mean) | flag |
|---|---|---|---|---|---|---|
| 42 | 40 | -0.0010 | -0.0001 | +0.0001 | 0.9525 | LOW POWER |
| 7 | 7 | +0.0021 | +0.0025 | -0.0000 | 0.1230 | EVALUABLE DEGIL |
| 123 | 117 | +0.0016 | -0.0000 | +0.0001 | 0.0025 | LOW POWER |
| 2026 | 0 | - | - | - | - | sinyal yok |
| 999 | 11 | +0.0018 | -0.0003 | +0.0001 | 0.1190 | EVALUABLE DEGIL |

Not: t=1h (h=12). Small-n (7/999) EVALUABLE DEGIL; 2026 sinyal yok.

## 7. SELL Results

| seed | n | rl_mean | rl_med | ctrl_med-med | mc_p(mean, low=good) | flag |
|---|---|---|---|---|---|---|
| 42 | 40 | -0.0010 | -0.0002 | +0.0001 | 0.0600 | LOW POWER |
| 7 | 7 | +0.0017 | +0.0014 | -0.0000 | 0.8460 | EVALUABLE DEGIL |
| 123 | 116 | +0.0025 | +0.0007 | +0.0000 | 1.0000 | LOW POWER |
| 2026 | 0 | - | - | - | - | sinyal yok |
| 999 | 10 | -0.0012 | +0.0014 | +0.0001 | 0.1545 | EVALUABLE DEGIL |

Pooled SELL (seed-cluster): median-diff metric +0.0008, CI95 [+0.0001, +0.0014], lower>0=True. BUYUYSE → SELL sonrasi fiyat KONTROLDEN YUKARI → sell sinyali onegorucu degil (hatta ters yonde).

## 8. Horizon Curve (BUY forward-return medians: RL vs control)

| h | seed123 RL_med | 123 ctrl_med | seed42 RL_med | 42 ctrl_med | drift_all |
|---|---|---|---|---|---|
| 5m (1) | -0.0000 | +0.0000 | +0.0001 | +0.0000 | +0.0000 |
| 15m (3) | -0.0003 | +0.0000 | -0.0008 | +0.0000 | +0.0000 |
| 1h (12) | -0.0000 | +0.0001 | -0.0001 | +0.0001 | +0.0002 |
| 3h (36) | +0.0000 | +0.0001 | +0.0001 | +0.0001 | +0.0005 |
| 6h (72) | +0.0008 | +0.0001 | -0.0008 | +0.0003 | +0.0009 |
| 20h (240) | +0.0002 | +0.0010 | +0.0060 | +0.0014 | +0.0031 |
| 60h (720) | +0.0188 | +0.0023 | +0.0066 | +0.0038 | +0.0096 |

Basit trend (herhangi bir random step'in beklenen 1h getirisi) +0.015% — RL 123 bul-cell'inde median <= kontrol.

## 9. Regime Results (BUY h=12, descriptive)

| seed | regime | n | rl_mean | ctrl_mean-med | mc_p |
|---|---|---|---|---|---|
| 42 | sideways | 4 | -0.0040 | +0.0001 | 0.9890 |
| 42 | bull | 22 | -0.0010 | +0.0002 | 0.8830 |
| 42 | bear | 14 | -0.0002 | +0.0003 | 0.6660 |
| 7 | bull | 5 | +0.0011 | +0.0002 | 0.2935 |
| 7 | bear | 1 | +0.0025 | -0.0001 | 0.2145 |
| 7 | sideways_high_vol | 1 | +0.0066 | -0.0004 | 0.0555 |
| 123 | sideways | 4 | -0.0012 | +0.0001 | 0.8700 |
| 123 | bull | 96 | +0.0019 | +0.0002 | 0.0010 |
| 123 | bear | 14 | +0.0006 | +0.0003 | 0.4075 |
| 123 | sideways_high_vol | 3 | +0.0028 | -0.0004 | 0.1010 |
| 999 | sideways | 1 | +0.0010 | +0.0000 | 0.2665 |
| 999 | bull | 7 | +0.0014 | +0.0001 | 0.2090 |
| 999 | bear | 3 | +0.0030 | +0.0003 | 0.1450 |

Degil: rejim alt-grupları kucuk-n → betimsel (edge-lerden sayılmaz).

## 10. Random-Control Comparison (per-seed h=12 details)

| seed | mwu_p | welch_p | mean_diff | CI95(welch) | CI95(boot) | cohen_d | cliff | power | dirfrac | binom_p |
|---|---|---|---|---|---|---|---|---|---|---|
| 42 | 0.9043 | 0.4956 | -0.0008 | [-0.0031, 0.0015] | [-0.0030, 0.0014] | -0.153 | +0.016 | 0.10 | 0.475 | 0.8746 |
| 7 | 0.4557 | 0.4265 | +0.0037 | [-0.0062, 0.0136] | [-0.0040, 0.0120] | +0.443 | +0.265 | 0.12 | 0.571 | 1.0000 |
| 123 | 0.9646 | 0.5029 | +0.0010 | [-0.0019, 0.0038] | [-0.0017, 0.0039] | +0.088 | -0.003 | 0.10 | 0.496 | 1.0000 |
| 999 | 0.7928 | 0.7882 | +0.0009 | [-0.0063, 0.0081] | [-0.0046, 0.0076] | +0.117 | -0.074 | 0.06 | 0.455 | 1.0000 |

## 11. Baseline / FreqAI Comparison

- B&H: gross 83.892%, net 83.341% (n=1 trade).
- Drift (1h): +0.0154% — trend-aware kontrol referansi.
- Phase3 baseline: **N/A** (per-entry trade artefacti yok; comparison.json metrics-only; Gameplan baseline ≈ B&H → B&H satırı).
| seed | FreqAI n(1h) | FreqAI mean(1h) | RL mean(1h) | RL n |
|---|---|---|---|---|
| 42 | 136 | +0.0010 | -0.0010 | 40 |
| 7 | 141 | +0.0007 | +0.0021 | 7 |
| 123 | 140 | +0.0006 | +0.0016 | 117 |
| 2026 | 126 | +0.0002 | 0 | 0 |
| 999 | 127 | +0.0005 | +0.0018 | 11 |

## 12. Exposure vs Timing Decomposition (descriptive)

RL_net ≈ DRIFT(E·R_BH) + TIMING − FRICTION; TIMING_reentry = RL_net − REENTRY_net (4.16 anchor). HEPsi compounding dartigi → approximate.
| seed | E | RL_net | DRIFT_g | TIM_g | FRICTION | TIM_net | REENTRY | TIM_reentry |
|---|---|---|---|---|---|---|---|---|
| 42 | 0.4046 | +0.3750 | +0.3394 | +0.1817 | +0.1461 | +0.1839 | +0.6228 | -0.2478 |
| 7 | 0.0002 | -0.0272 | +0.0001 | -0.0067 | +0.0207 | -0.0067 | +0.4213 | -0.4485 |
| 123 | 0.9958 | +0.1875 | +0.8354 | -0.2354 | +0.4125 | -0.2299 | +0.1470 | +0.0405 |
| 2026 | 0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| 999 | 0.9941 | +0.8080 | +0.8340 | +0.0188 | +0.0448 | +0.0243 | +0.7604 | +0.0476 |

## 13. Statistical Results

- FDR (BUY h12, BH): {'42': 1.0, '7': 0.246, '123': 0.0033, '999': 0.119} → yalnizca 123 q<0.05 (0.0033) ama LOW POWER ve median bazında degil; C2'yi tek basına gezirmez.
- Pooled BUY (seed-cluster, 10k): metric +0.000471, CI95 [-0.000325, +0.001861], lower>0=False (seed bagimsizligi VARSAYILMAZ).
- Pooled SELL: CI95 [+0.000148, +0.001408], lower>0=True (sell tarafında ters yön).

## 14. Evaluable / Not Evaluable

- EVALUABLE (n≥12): 42 (n=40), 123 (n=117) — ikisi de LOW POWER (power<0.80).
- EVALUABLE DEGIL: 7 (n=7), 999 (n=11) — 1h sonuclari edge lehine okunamaz (DESIGN F1).
- 2026: 0 BUY/sell → sinyal-yok seed; 'edge yok' kantı DEĞİL (prereg note).

## 15. Edge Decision (preregistered C1..C4)

- C1_pooled_lower_CI_gt_0=False
- C2_bh_q_lt_0.05=True
- C3_ge_3of5_seeds_same_dir=False
- C4_control_sanity=True
- Detail: {'min_q': 0.0033, 'directed_seeds': 1, 'n_signal_seeds': 4}

**KARAR: DECISION-LEVEL EDGE YOK** — pre-registered kurallar disinda sonradan kriter eklenmedi.

## 16. Limitations

- n cok kucuk (7, 11) seed'ler istatistiksel olarak degerlendirilemedi.
- 123'ün mc_p(mean) sinyali asimetrik 1-2 buyuk event, median ve power tarafini tutmuyor.
- Pooled uc-yok test n=4 UCSI seed; cluster CI genis.
- FreqAI only BTC/USDT trades (136-141/csv); farkli seed model hiperparametreleri; yalnizcı tanımlayıcı satır.
- Decomposition approximate (compounding); reentry anchor 4.16 konvansyonu.
- 2023H1 tek piyasa tecrübesi; genellenebilirlik iddiasi yok.

## 17. Protocol Impact

- Alpha Gate **LOCKED-DIAGNOSTIC** kalır; 4.18'de selection criterion yapılMADi.
- Locked threshold'lar (Sharpe>=0.80, gap<0.35, 30g, power 0.80): DEĞİŞMEZ.
- Env/reward/action-space/normalizer DEĞİŞTİRMEDİ; training/tuning YOK.
- 4.18 yalnızca YENİ dosyalar: scripts/phase418_*, tests/test_phase418.py + artefacts/REPORT.

## 18. Final Test B Protection

- Final Test B: İNDİRİLMEDİ · AÇILMADI · ÇALIŞTIRMADI · METRIKLERI HESAPLANMADI. Hiçbir 4.18 script'i Final B path'ine referans içermiyor.

## SONUÇ (A / B / C — ayrı ayrı)

**A) Decision-level predictive edge var mı? → DECISION-LEVEL EDGE YOK**
   (BUY 1h: pooled lower-CI ≤ 0, >=3/5 seed ayni yonde DEĞİL; 123 tek pozitif-asimetrik; 7/999 EVALUABLE DEGIL.)
**B) Economic trading edge var mi? → BU FAZIN KONUSU DEGIL.** 4.17 locked A-gate: E1 mean 0.225 < 0.80 → FAIL; bu fazda yeni eğitim/ölcüm yok; karar-duzeyi bulgular ekonomik edge olarak satılamaz.
**C) RL sonucu market exposure/drift ile açiklanabilir mi? → BÜYÜK ÖLÇÜDE EVET.** 4.16/4.17 ile tutarli: e.g. 999 net +80.8% ≈ E×R_BH 82.8% ≈ reentry 76.0%; 123 net 18.8% ama friction 41.3% ile driftin büyük kısmı turnover ile yenilmiş; karar-duzeyi sinyal de kontrol-medyaninin altında/etrafında.
