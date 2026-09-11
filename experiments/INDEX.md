# EXPERIMENT INDEX — Phase 1–15 (doğrulanmış kayıt; yorum YOK)

| Phase | Hypothesis | Data | Result | Verdict | Holdout status | Repro artifact |
|-------|-----------|------|--------|---------|----------------|----------------|
| P1 dry-run | Paper altyapı çalışır | Canlı Binance | 9/9 verifier | PASS | yok | phase01_closure_2026-09-04.md |
| P2 WF baseline | RSI/SMA kuralı edge üretir | 18 pair 5m, 9 fold | fold netleri çoğunlukla negatif | FAIL | A açılmadı | RESULT_2026-09-04.md + folds.csv |
| P3 FreqAI | RF+H=12 öngörür | BTC 5m, 5 seed | Sharpe ≈−25, fee-ölümü | FAIL | A TÜKETİLDİ | RESULT_2026-09-04.md |
| P4 RL | PPO policy + decision-alfa | BTC 5m + artefakt replay | 18/20 HOLD; 4.18 edge-YOK | FAIL | B ÇALIŞTIRILMADI | RESULT*.md + tuning47/ |
| P5 ML-44 | 44 hücreden biri FDR-güçlü edge bulur | BTC 5m/15m | 0/44 q<0.05 (E014 edge −0.69) | FAIL | P5 ayrıldı (o dönem) | NIGHT_RUN_REPORT.md + results/*.json + oof500.parquet |
| 6A cross-asset | Breadth/dispersion incremental bilgi taşır | 7 majör 5m | ΔPSS −0.000038, CI sıfır-içerir | FAIL | açılmadı | RUN_REPORT_6A.md + results6a/ |
| 6B funding | Settled funding incremental bilgi taşır | fapi fundingRate ~3.8k | ΔPSS −0.000037; NEW AUC 0.536 | FAIL | açılmadı | RUN_REPORT_6B.md + results6b/ |
| 6C OI | OI incremental bilgi taşır | Vision metrics 5m-snap | STOP (glitch) → revizyon-koşu FAIL | FAIL | açılmadı | RUN_REPORT_6C.md + results6c/ |
| P7 H48 | 4h swing ekonomikleşir | BTC 5m (aynı) | θ=+5.47 kırılgan-kuyruk; gate FAIL | FAIL | açılmadı | PHASE_07_RUN_REPORT.md + results7/ |
| P8 cost | C=0.003 savunulabilir mi? | tarife dokümanları | A) DEFENSIBLE (20–30bp bandı) | PASS(scout) | yok (doküman) | PHASE_08_COST_SCOUT.md |
| M.20 re-eval | H48, futures-maliyetle edge üretir mi? | oof7 + funding arşivi (fit YOK) | net +0.44% ama MaxDD 0.90 → B | B: zayıf/doğrula-gerekir | açılmadı | M20_REEVAL.json/.md |
| M.20-confirm | M.20 pozitifi replike olur mu? | 2025H1 feather (hash-pinli) | θ=−10.22, net<0, tüm gate FAIL | FAIL=NOT-CONFIRMED | **P5 TÜKETİLDİ** | results_confirm/ + RESULTS.md |
| P9 carry | Delta-nötr hasat primi toplar | UM 1h + funding | statik tasarım likide (9.58×) | STOP→CLOSED | açılmadı | PHASE_09_LOCK.md + PREFLIGHT.json |
| P10 calendar | 3 deterministik kural drift üretir | spot 5m (takvim) | net<0 hepsi, q=1.0 | CLOSED | açılmadı | PHASE_10_RESULTS.md + results10/ |
| P11 basis | Quarterly yakınsama primi | 12 CM kontrat | net −6.15 BTC, q=0.39 | FAIL | açılmadı | PHASE_11_RESULTS.md + results11/ |
| P12 maker | Maker execution kurtarır mı? | — (veri YOK) | STOP (L2/book yok; spot indirimsiz) | STOP | açılmadı | PHASE_12_MAKER_SCOUT.md |
| P13 on-chain | Exchange-flow edge | — (PIT-tarihçe yok) | STOP (2020–23 PIT imkansız) | STOP | açılmadı | PHASE_13*_ONCHAIN/GATE.md |
| P14 micro-flow | AggTrades toksisitesi taşınır mı? | 1-ay aggTrades (2023-02) | 1s'te bile +0.005bp → FAST DECAY/STOP | STOP | açılmadı | PHASE_14_* (scout+pilot) |
| P15 audit | Kapanış denetimi | tüm faz dosyaları | STOP ALPHA SEARCH | — | B/C korunuyor | PHASE_15_MASTER_AUDIT.md + matris |

Notlar: M.20 re-eval ve 6C-revizyon-koşusu ayrı satır DEĞİL (ana hattın devamı; yukarıda gömülü). `next_phase/NEXT_PHASE_DESIGN.md` GÜNCEL DEĞİL (Phase-10 tasarımını gösterir). `phase_10_paper/` ve `phase_06_x_layer/` BOŞ (başlanmamış iş).
