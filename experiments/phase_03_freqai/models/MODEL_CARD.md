# Faz 3 — Model Kartı (kilitli, 2026-09-04)

Kaynak: `src/freqai/model.py:1`. Amaç "en iyi model" DEĞİL; kontrollü baseline.

- **Sınıf:** `RandomForestClassifier` (tek model, çeşitlilik yok)
- **Hiperparametreler (kilitli):**
  - `n_estimators=200`, `max_depth=8`, `min_samples_leaf=50`
  - `class_weight="balanced"`, `n_jobs=1`, `random_state=<seed>`
  - `n_jobs=1` gerekçesi: bit-exact reproducibility (`n_jobs=-1` paralel
    indirgemede ~1e-16 dalgalanma yapar; test edildi). Compute tercihi, model seçimi değil.
- **Seed'ler (kilitli):** `[42, 7, 123, 2026, 999]` — her seed ayrı koşum, sonuçlar ayrı kaydedilir.
- **Sinyal:** `proba >= 0.5 → 1 (long)`, yoksa `0 (flat)`.
- **Trade simülasyonu (deneyde):** sinyal 1 + flat → aç; sinyal 0 → kapat;
  ROI %2 / SL -%10 (Baseline ile aynı ekonomi); fee 0.001×2, slippage 5bps varsayımı.
- **Eğitilmiş model YOK** (bu aşamada): `models/` yalnızca kart + `.gitkeep` içerir.

Doğrulama: `test_seed_reproducibility` — aynı seed bit-identical proba — PASS.
