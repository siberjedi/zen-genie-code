# M.20 REVIEW — 6A Lock Finalization (REVIEW, APPROVAL DEĞİL)

**Statü:** 5 açık karar resolved → FINAL LOCK CANDIDATE hazır. M.20 APPROVED
denmedi; final onay otoritenindir.

## 1. Beş kararın çözümü

### Karar 1 — BASE: E032-verbatim canonical kilitlendi
Phase 5 BASE tanımı: BASEL1 kolu (majority/mean, B3/L1) — no-skill referansı;
6A'daki BASE ise OHLCV-bilgi referansıdır (farklı rol, karışmaz).
E032 (B3/L1/M2/seed42): PSS −0.002117, edge −0.706, AUC 0.6811, IC 0.0452.
E014 (B1/L1/M2/seed42): PSS −0.002069, edge −0.690, AUC 0.6793, IC 0.0429.
Tek fark blok (B1 7 feat vs B3 28 union); deltalar gürültü mertebesinde
(Δedge +0.016, ΔAUC −0.0018), iki hücre de tüm gate'lerde FAIL.
E032 seçildi: tam-OHLCV yapısal referans + aynı-VAL seçim yanlılığından kaçınma.
Tek tanım, alternatif elendi.

### Karar 2 — Universe: 7 asset kilitlendi
ETH, BNB, XRP, ADA, DOGE, LTC, BCH. SOL ve diğerleri primary dışı.
Bağlayıcı kural (§5): listeleme ≤2019-12-31 + kesintisiz 2020→2023H1 5m +
majör likidite; bozan sembol çıkarılır (doldurma/proxy yok).

### Karar 3 — Primary model: M2 tek
RF frozen config verbatim. M1/M3 primary dışı; M3-FULL refit yalnızca
betimsel robustness, PASS/FAIL'e etkisiz.

### Karar 4 — Incremental criterion: ΔCI95 alt > 0 kilitlendi
FULL−BASE için ΔPSS ve Δedge/cost bootstrap %95 CI (10k, seed 42);
alt sınır > 0 şart. CI sıfırı içerirse PASS yok. AUC tek başına PASS üretemez.
Fallback kaldırıldı.

### Karar 5 — 15m secondary çıkarıldı
Scope yalnızca 5m → 1h. Yeni secondary family yok; tek primary familya (3 test).

## 2. Final BASE
E032-verbatim: B3 + L1 + M2 + seed 42 + Phase-5 splitleri (n_train 314571,
n_val 51798). Reprodüksiyon gate'i (§9-6, tolerans 1e-9) geçmeden ilerlenmez.

## 3. Final universe
§Karar-2'deki 7 sembol + bağlayıcı listing/availability kuralı.

## 4. Final feature set
6 family (breadth_1, breadth_12, dispersion_12, btc_rel_12, ethbtc_chg_12,
corr_regime-288); formüller §6–7; BTC-öz momentum yok.

## 5. Final primary model
M2 frozen (200/8/50/balanced/n_jobs=1/seed42). Tuning yok.

## 6. Final horizon
Primary 5m → 1h (H=12, L1). Exploratory: L0/L2 + ufuklar 3/36/72 (gatesiz).

## 7. Final incremental criterion
§Karar-4. PASS iff FULL gate zinciri (§20 aynen) + ΔCI alt > 0.

## 8. Protected test policy
P5=2025H1, B=2024H1, C=2024H2, A=2023H2 (tüketildi): load/score/selection YOK.
İndirme 2023-06-30 sonrasını kapsamaz. 6A PASS bile P5'i otomatik açmaz —
ayrı M.20 final-test kararı gerekir.

## 9. Blocker taraması (deney öncesi)
- [x] Kararlar 5/5 resolved (onay pending — blocker değil, süreç adımı)
- [x] Korumalar aynen korunuyor (4 pencere kilitli)
- [x] Yeni eşik yok (Phase-5 değerleri aynen)
- [x] Deney/indirme/fit/backtest çalıştırılmadı
- [x] Commit/push yok; scout dosyaları değişmedi
- [ ] **Final M.20 onayı (otoritede)** — tek bekleyen adım

Blocker YOK. Onay gelmeden 6A'ya ait hiçbir adım çalıştırılamaz.

**READY FOR FINAL M.20 APPROVAL**
