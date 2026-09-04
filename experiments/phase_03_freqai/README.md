# Faz 3 — FreqAI Hazırlık (readiness-only, 2026-09-04)

> **Durum:** Pipeline KURULU, deney KOŞULMADI, Final Test A'ya DOKUNULMADI.
> Eşikler (`config/experiment.yaml:57-61`) ve `PROTOCOL.md` değişmedi.

## Amaç
Dondurulmuş BaselineStrategy'a karşı FreqAI'nin OOS ek değeri var mı?
Şu an SADECE hazırlık + validasyon; seçim/optimizasyon YOK.

## Pipeline
`Market OHLCV → Features → Label → Train → Validation → Signal → Backtest → OOS eval`
Kod: `src/freqai/` (`features.py`, `labels.py`, `splits.py`, `model.py`,
`pipeline.py`, `compare.py`). Tanımlar: `features.md`, `label.md`, `models/MODEL_CARD.md`.

## Splitler (kilitli, `config/experiment.yaml:10-16`)
- TRAIN: 2020-01-01 → 2022-12-31 (5-fold CV burada, `folds/cv_folds.csv`)
- VALIDATION: 2023-01-01 → 2023-06-30 (seçim SADECE burada)
- FINAL_A: 2023-07-01 → 2023-12-31 (**YASAK** — guard: `splits.assert_no_final_leak`, ABORT)

## CV × Seed
- 5 expanding takvim fold'u (train-içi) × 5 seed `[42, 7, 123, 2026, 999]` = 25 koşum (deneyde).
- Seed stability eşiği: `sharpe_std_across_5_seeds < 0.25` (değişmedi).

## Karşılaştırma (kilitli tanım, sonuç yok)
- Birincil: `delta = FreqAI_val_Sharpe − Baseline_val_Sharpe` (aynı pencere/universe/maliyet).
- Eşikler: delta ≥ 0.30, WF win rate ≥ 0.60, MaxDD ≤ 0.20, seed_std < 0.25.
- İstatistik: FDR + Cohen's d + power + overlap (`src/backtest/evaluate.py` aynen).
- "Anlamlı fark yok" ≠ "edge yok" (effect size + power raporlanacak).

## Validasyon (bu aşama)
`tests/test_freqai_readiness.py` — 9 test, ALL PASS:
feature/label leakage, NaN (211 kayıp), split+guard, seed reproducibility,
gerçek-veri guard (18/18 < 2023-07-01, 12 boş), metrik entegrasyonu, CV yapısı, smoke.

## Çıktılar
`config_snapshot.*`, `features.md`, `label.md`, `folds/`, `models/`, `results/` (şema),
`run_metadata.json`. Eğitilmiş model YOK, sonuç YOK.
