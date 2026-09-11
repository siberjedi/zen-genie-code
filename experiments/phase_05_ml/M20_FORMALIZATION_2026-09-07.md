# PHASE 5 — M.20 FORMALIZATION (KARAR KAYDI)
## Tarih: 2026-09-07 · Statü: RESERVED/LOCKED-in (resmî M.20 onayı user)

> Bu belge, Phase 5 (phase_05_ml) için kullanıcının verdiği M.20 kararlarını
> protokol kayıtlarına RESMÎ olarak işler. AŞAMA KAPSAMI: yalnızca kayıt +
> holdout rezervasyonu + izole 2025H1 indirme + guard. NO TRAINING · NO TUNING ·
> NO FEATURE SELECTION · NO MODEL SELECTION · NO THRESHOLD TUNING · NO BACKTEST ·
> NO FINAL TEST EVALUATION.

---

## 1. Kullanıcı Kararları (kaynak: M.20 DECISION REVIEW + soru-cevap turu)

| # | Karar | Değer / Kural |
|---|---|---|
| 1 | Phase 5 final holdout | **2025H1 = 2025-01-01 → 2025-06-30** (`FINAL_TEST_P5`) |
| 2 | Final Test B (2024H1) | **KORUNUR** — Phase 5 tarafından KULLANILMAZ (UNTOUCHED) |
| 3 | 2024H2 (Final C) | **KORUNUR** — UNTOUCHED |
| 4 | Threshold paketi | DESIGN_500.md'deki haliyle M.20'ye sunulan paket KORUNUR; sonuçlara bakarak DEĞİŞMEZ |
| 5 | Multiple comparison | **4 FDR ailesi korunur**; arm-wise margin / effective-test-count caveat raporda tutulur |
| 6 | Selection kuralı | `argmax(edge/cost)` frozen kural; selection-leakage uyarısı + holdout koruması dokümante edilir |

---

## 2. M.20 Kapsamında FROZEN OLANLAR (bu fazın ön-kaydı)

- **Experiment matrix (frozen):** 36 birincil cell (E001–E036; 4 blok × 3 label × 3 model)
  + 3 baseline + 8 ikincil TF (S001–S008) = **44 formal test**; birincil 36 PASS/FAIL belirler.
- **Candidate selection rule (frozen):** `argmax(edge/cost)`, tie-break düşük cell ID.
- **Thresholds:** PSS (top-decile mean future return − C); `edge/cost ≥ 1.2`;
  `AUC ≥ 0.55`; `rank-IC ≥ 0.01`; Kendall tau > 0; seed sign-consistency ≥ 2/3;
  Cohen d ≥ 0.30; power ≥ 0.80; BH-FDR q < 0.05; WF ≥ 0.60.
  - Protokol-içi (config'e bağlı, M.20 gerektirmez): BH-FDR α=0.05, d≥0.30,
    power 0.80, WF≥0.60, cost parametreleri (fee 0.001×2 + slip 5bps×2 → C=0.003),
    bütçe cap (rl_budget.max_train_hours=12 emsali).
  - Yeni-pencere/sayı kaynaklı (bu M.20 onayına bağlı): PSS-stage-primary metrik,
    `edge/cost ≥ 1.2`, `AUC ≥ 0.55`, `rank-IC ≥ 0.01`, seed 2/3 (Sharpe-based
    seed_stability'dan ayrı aile), LGBM→XGBoost kurulum fallback'i.
- **FDR families (4):** L0 kol 12 cell · L1 kol 12 cell · L2 kol 12 cell
  · ikincil TF 8 cell. Arm-wise margin: 3 bağımsız kol birlikte kontrolde
  P(≥1 yanlış-pozitif kol) ≈ %14 → PASS kolunun arm-gate'i marjla geçme şartı;
  "nominal 44, efektif << 44" notu raporda.

## 3. Aşama 1 kapsamında DEĞİŞTİRİLEN / EKLENEN dosyalar

- `config/experiment.yaml` — `splits.phase_05_ml` bloğu eklendi
  (`train`, `validation`, `final_test_P5=2025H1`, `note`). Mevcut kilitli
  split/parametre değerlerine DOKUNULMADI (yalnızca yeni faz bloğu eklendi).
- `experiments/phase_05_ml/M20_FORMALIZATION_2026-09-07.md` — bu belge.
- `DESIGN_500.md` — statü başlığı M.20 formalize hâle güncellendi.

## 4. Diğer fazların final pencerelerinin DOKUNULMAZLIK teyidi

- **Final Test A (2023H2):** FreqAI tarafından TÜKETİLDİ — Phase 5 KULLANMAZ.
- **Final Test B (2024H1):** RL'e ayrıldı; **KORUNUR, Phase 5 tarafından indirilmez/kullanılmaz.**
- **Final Test C (2024H2):** karşılaştırma; **KORUNUR, Phase 5 indirmez/kullanmaz.**

---

**LOCK NOTU:** Yukarıdaki kararlar kullanıcı tarafından verilip RESERVED statüsündedir.
Resmî M.20 protokol kilidi (final) + 2025H1 indirme onayı user'ındır; Phase 5 deney
pipeline'ı bu kayıt RESMÎ onaylanmadan çalıştırılmaz.

**READY FOR USER DECISION (M.20 kayıt — pipeline kapalı)**
