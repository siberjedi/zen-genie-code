# PHASE 19 — ALPHA EVIDENCE MATRIX

**Kaynak:** P1–P18C sonuçları (Phase 15 master audit + 18C geçerli koşum-2 + M.20).
Sınıflandırma: FALSIFIED (karar-verici test, edge yok) · ECONOMICALLY FAILED
(sinyal kanıtı var ama maliyet/benchmark/risk öldürdü) · DATA BLOCKED (veri/PIT
engeli — hüküm YOK) · PARTIALLY TESTED · UNTESTED.

| Family | Phase | Hypothesis | Data | Horizon | Gross | Net | Cost | İstatistik | Holdout | Primary Failure | Disposition |
|--------|-------|-----------|------|---------|-------|-----|------|-----------|---------|-----------------|-------------|
| OHLCV/technical | P2 | RSI/SMA kuralı edge üretir | 18 pair 5m | 5m | pozitif brüt (kısmen) | fold netleri negatif | 30bp+ | fold tablosu | — | cost/turnover | FALSIFIED |
| ML prediction | P3, P5 | RF 5m–15m H12'yi öngörür | BTC 5m/15m | 5m–15m | brüt var ama zayıf | Sharpe −25; 0/44 FDR | 30bp | FDR-4 aile, q=1.0 | FINAL_A (CONSUMED) FAIL | predictive+cost | FALSIFIED |
| RL decision | P4 (+4.18) | PPO karar-level alpha | BTC 5m | 5m | — | 18/20 HOLD; C1/C3 fail | env-lock | MC p, Welch, power | FINAL_B rezerv (18C'de ayrı deneye verildi) | decision quality | FALSIFIED |
| Cross-asset features | 6A | breadth/dispersion/corr bilgi taşır | 7 majör 5m | 5m/H12 | — | ΔPSS≈0, edge −0.72 | 30bp | FDR-3, CI∋0 | — | predictive | FALSIFIED |
| Funding (sinyal) | 6B | settled funding bilgi taşır | fapi ~3.8k | 5m/H12 | — | ΔPSS≈0 | 30bp | AUC 0.536 | — | predictive | FALSIFIED |
| Open interest | 6C | OI bilgi taşır | Vision metrics | 5m/H12 | — | gate FAIL (revizyon-koşusu) | 30bp | CI∋0 | — | predictive | FALSIFIED |
| 4h event swing | P7 + M.20 | H48 skor-event ekonomikleşir | BTC 5m | 48h | θ +5.47 (artefakt) | PSS<0 | 30bp→13.4bp | θ12 −5.91; MaxDD 0.963 | FINAL_P5 (CONSUMED) θ=−10.22 | tail + holdout | FALSIFIED |
| Calendar/session | P10 | weekend/overnight/fade | spot 5m | günlük | — | 3 kural net<0 | 30bp | q=1.0 | — | predictive | FALSIFIED |
| Futures basis | P11 | quarterly yakınsama primi | 12 CM kontrat | çeyrek | ±5bp yakınsama var | −6.15 BTC | 30bp | d=0.079, q=0.39 | — | cost (brüt < 30bp) | ECONOMICALLY FAILED |
| Carry/delta-neutral | P9 | funding+basis hasatı | UM 1h + funding | haftalık | — | likidasyon 9.58× | — | — | — | survival/risk | ECONOMICALLY FAILED |
| Micro trade-flow | P14 | aggTrades bilgi taşır | 187M trade | 1s–5m | +0.005bp (1s) | ~0 | 30bp | hızlı decay | — | horizon/cost | FALSIFIED (economic) |
| Long-only trend + vol-target | P17/18C | crash-avoidance BH'yi yener | BTC 5m→4H/1D | 4H/1D | Sharpe 0.73–2.15 | +%9–36 mutlak | 30bp (G7 ✓) | FDR q>0.10 | FINAL_B (CONSUMED) — 6/6 gate fail | **benchmark (G4) + stability (G5)** | ECONOMICALLY FAILED |
| On-chain | P13 | zincir akışı öngörür | Glassnode/CQ | günlük | — | — | — | — | — | PIT-tarihçe yok | DATA BLOCKED |
| L2/order-book | P12/16 | kitap şekli bilgi taşır | ücretli | sn–dak | — | — | — | — | — | ücretli veri | DATA BLOCKED |
| Maker execution | P12 | indirimli fill | kendi log | — | — | — | — | — | — | veri yok | DATA BLOCKED |
| News/sentiment/X | P16 | haber akışı | yok | — | — | — | — | — | — | arşiv yok | DATA BLOCKED |
| Liquidations flow | P16 | likidasyon akışı | ücretli+seyrek | — | — | — | — | — | — | veri | DATA BLOCKED |
| Options vol premium | P16 | vol prim hasatı | Deribit | — | — | — | — | — | — | veri yükü+marjin | UNTESTED (F-elendi) |
| Cross-exchange arb | P16 | fiyat farkı | çok-venue | — | — | — | — | — | — | HF-latency | UNTESTED (F-elendi) |
| ETF/makro akış | P16 | kurumsal akış | 2024+ | — | — | — | — | — | — | pencere dışı | UNTESTED (F-elendi) |
| Mean reversion (sistematik) | P10 (fade) | MR primi | spot 5m | günlük | — | fade FAIL | 30bp | q=1.0 | — | yalnızca 1 deterministik form testli | PARTIALLY TESTED |
| Haftalık cross-sectional long-only | — | top-k seçim | **mevcut** (6A+funding+OI) | haftalık | — | — | — | — | — | hiç koşulmadı | **UNTESTED** |

## Özet sayılar

- **FALSIFIED:** 13 family (P2, P3, P4, P5, 6A, 6B, 6C, P7/M.20, P10, P14, 18C)
- **ECONOMICALLY FAILED:** 3 (P11, P9, 18C-long-only-trend)
- **DATA BLOCKED:** 5 (on-chain, L2, maker, news/X, liquidations)
- **PARTIALLY TESTED:** 1 (mean reversion — yalnızca fade formu)
- **UNTESTED:** 4 (options, cross-venue arb, ETF/makro — F-elendi; **weekly cross-sectional long-only — veri-feasible**)

FALSIFIED ≠ DATA BLOCKED (kategoriler ayrı tutuldu): FALSIFIED = karar-verici
test sonucu hüküm; DATA BLOCKED = veri/PIT engeli, hüküm yok.