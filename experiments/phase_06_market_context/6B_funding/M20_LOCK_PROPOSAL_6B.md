# M.20 LOCK PROPOSAL — Phase 6B Funding Rate (TASLAK, ONAY YOK)

**Statü:** ÖNERİ. M.20 onayı verilmedi; onay gelmeden deney çalıştırılmaz,
veri indirilmez, model eğitilmez, backtest yapılmaz, holdout açılmaz.
**Kapsam:** SADECE 6B (funding). 6A sonuçları değiştirilmez; 6A dosyalarına
dokunulmaz. 6C+ dahil değildir.
**Referanslar:** Phase-6 scout (DESIGN_600, SOURCE_AUDIT, DATA_FEASIBILITY,
LEAKAGE_MATRIX, EXPERIMENT_OPTIONS, PRIORITY_MATRIX, PHASE_06_SCOUT_REPORT),
6A lock/review/run/results, DESIGN_500, TRAIN_VALIDATION_RESULTS,
NIGHT_RUN_REPORT, DESIGN_418, PROTOCOL, config/experiment.yaml.
(Not: "4.19" başlıklı ayrı doküman yok; 4.18 tasarım+rapor baz alındı.)

## 1. Research question

Perpetual futures funding rate bilgisi, BTC'nin kendi OHLCV bilgisine
eklenince maliyet sonrası out-of-sample incremental edge sağlıyor mu?
(5m grid, 1h forward getiri, locked cost C=0.003.)

## 2. H1

FULL kolu (BASE OHLCV + funding), BASE kolundan ekonomik olarak anlamlı
ölçüde ayrışır: ΔPSS = PSS_FULL − PSS_BASE > 0 (bootstrap CI95 alt sınırı > 0,
§21) VE FULL kolu Phase-5 gate zincirini tam geçer (§20).

## 3. H0

Funding incremental bilgi taşımaz (ΔPSS CI95 sıfırı kapsar ve/veya FULL gate
zincirini geçemez). Sonuç cümlesi: **"FUNDING INCREMENTAL EDGE YOK."**

## 4. BASE / NEW / FULL ablation (deneyin ana testi)

| Kol | Feature | Label | Model | Seed | Rol |
|-----|---------|-------|-------|------|-----|
| BASE | B3 (28 OHLCV union, frozen) — **E032-verbatim canonical** (6A ile aynı tanım) | L1 | M2 | 42 | Referans |
| NEW | 5 funding feature (§6), BTC OHLCV YOK | L1 | M2 | 42 | Tanısal (tek başına raporlanır, BASE'in yerine geçmez) |
| FULL | B3 + 5 funding | L1 | M2 | 42 | Aday (karar FULL−BASE farkıyla verilir) |

Ana test = FULL vs BASE. NEW-only destekleyici. AUC türü sinyal ile
net-after-cost ekonomik edge karıştırılmaz (§14).

## 5. Venue / sembol (universe karşılığı)

Tek kaynak (kilitli): **Binance USDⓈ-M BTCUSDT perpetual**,
`GET /fapi/v1/fundingRate`. Gerekçe: hedef BTC spot ile aynı varlık, en derin
likidite, listeleme ~Eylül 2019 → locked pencereyi tam kapsar (deneyde ilk
fundingTime ≤ 2020-01-01 assert'i; sağlanmazsa STOP). Başka venue/sembol
eklenemez. Predicted/intraperiod funding KULLANILMAZ (scout: HIGH LEAKAGE RISK).

## 6. Feature set (5 adet, şişirme yok)

Settlement gridi: `T_j` = 00:00/08:00/16:00 UTC (8h). Ham seri: `R(T_j)` =
settled funding rate. Karar anı `t` (5m close) için kullanılabilir set:
`{R(T_j) : T_j ≤ t}` (B1 kuralı, §8).

- **F1 fund_rate:** `R(T*(t))`, `T*(t) = max{T_j ≤ t}` (son settled oran).
- **F2 fund_z_30:** `(R(T*) − mean(R son 30 settlement)) / std(R son 30 settlement, ddof=1)` (10-günlük pencere, settlement endeksli).
- **F3 fund_sign:** `sign(R(T*))` (+1/−1; tam 0 → 0).
- **F4 fund_abs_chg:** `|R(T*) − R(T*−1)|` (settlement-to-settlement değişim büyüklüğü).
- **F5 fund_persist:** aynı-işaretli ardışık settlement sayısı, 8'de cap'li (son ~64h doygunluğu).

Tümü trailing-only; 5m gridde 8h merdiven (ffill) olarak taşınır.

## 7. Feature formülleri — ek bağlayıcı detay

§6 tanımları bağlayıcıdır. z-score penceresi settlement-endekslidir (mum
endeksli 288-bar DEĞİL — kadans farkı; merdiven seride mum-penceresi yanlı
ağırlık verirdi). std ddof=1 (M2 için monoton dönüşüm, sonucu değiştirmez —
6A §7 emsali, raporda notlu). persist sayacı settlement sınırında sıfırlanır.
Oranlar ondalık (örn. 0.0001), yüzdeye çevrilmez.

## 8. Timestamp / availability / candle-close kuralları (matematiksel)

- `F_avail(t) = {R(T_j) : T_j ≤ t}`; 00:00/08:00/16:00 UTC 5m sınırlarına denk
  gelir (8h = 96×5m) → hizalama exact, yuvarlama yok.
- T_j anındaki candle (close = T_j): `R(T_j)` DAHİL (settlement o anda kesin).
- T_j'den önceki candle'lara `R(T_j)` yazmak = LEAK (dönem kapanmadan oran bilinemez).
- Aylık/REST çekimi tarihsel olduğundan ek availability sorunu yok; kural
  yalnızca grid-hizalaması içindir (LEAKAGE_MATRIX B1).

## 9. Leakage kontrolleri (pre-registered checklist)

1. Causality probe (`.shift(-`, centered rolling, ileri-fill taraması).
2. Feature[t] yalnızca `T_j ≤ t` settlement'ları (unit test: sentetik ileri-settlement).
3. Predicted/intraperiod funding kodda YOK (import/keyword taraması: "predicted", "mark_price" ile funding tahmini).
4. Settlement grid düzenliliği (8h; eksik settlement → STOP, doldurma yok).
5. İlk fundingTime ≤ 2020-01-01 kanıtı (coverage).
6. BASE E032-reprodüksiyon (tol 1e-9; 6A'da kanıtlı pipeline; tutmazsa STOP).

## 10. Label ve horizon (preregistered)

- **Primary:** L1 (Y > C, H=12 → 1h), 5m grid. Gerekçe: 6A ile aynı karar
  çerçevesi (karşılaştırılabilirlik, tek-familya FDR); "1h kullanımı" tahmin
  ufku olarak kilitlidir — tahmin hedefi 1h forward getiridir, funding ise
  yavaş-bağlam (rejim-benzeri) feature'dır. Ayrı 1h-candle pipeline AÇILMAZ
  (yeni split/metrik/familya karmaşası; 5m'e zorlama değil, hedef-ufku seçimidir).
- **Exploratory (gatesiz):** L0/L2; ufuk eğrisi 3/36/72 (FULL-L1 skorları sabit);
  funding × locked-rejim betimsel kırılımı (rejim classifier frozen, tanımsal).
- Label tanımı/off-by-one/label-bound Phase 5 ile birebir aynı.

## 11. Train / Validation / protected holdout

- TRAIN 2020-01-01 → 2022-12-31; VAL 2023-01-01 → 2023-06-30 (Phase 5/6A ile aynı).
- **KİLİTLİ:** FINAL_P5=2025H1, Final B=2024H1, Final C=2024H2, Final A=2023H2
  (tüketildi). 6B VAL-gated'dır; P5 rezerve kalır.
- İndirme 2020-01-01 → 2023-06-30 aralığını kapsar, sonrasını KAPSAMAZ
  (NO 2025H1 DOWNLOAD; startTime/endTime assert'li).

## 12. Frozen model ailesi

**Primary decision model: M2 tek model** (RF 200/8/50/balanced/n_jobs=1,
seed 42, verbatim). M1/M3 primary dışı; M3-FULL refit yalnızca betimsel
robustness (§22), PASS/FAIL'e etkisiz.

## 13. Hyperparameter tuning kuralları

**TUNING YOK.** Phase-5 değerleri verbatim. İhlal = protokol ihlali (Madde 10/20).

## 14. Primary metric

FULL PSS + edge/cost (Phase-5 tanımı) + §21 incremental kuralı. AUC tek başına
PASS üretemez.

## 15. Secondary metrics

AUC, PR-AUC, logloss, Brier, ECE, dir-acc, rank-IC, Kendall tau, Cohen d,
power, Welch CI, decile tablosu — 3 kol için raporlanır, gate üretmez.

## 16. Transaction cost / friction

C = 0.003 locked. Değişiklik yok.

## 17. Statistical tests

6A makinesi birebir: top-decile one-sample t-test (H0: mean ≤ C) → tek primary
BH-FDR ailesi (3 test, α=0.05); ΔPSS/Δedge için paired percentile bootstrap
CI95 (10k resample, seed 42); adayda 3-seed sign-consistency (42/7/123, ≥2/3) +
WF (365/90/90/90, expanding=false, ~9 fold, ≥0.60, overlap notuyla).

## 18. FDR family yapısı

- **Primary family (PASS yetkili, TEK):** {BASE, NEW, FULL} 5m/H12/L1/M2.
- Aile dışı (L0/L2, ufuklar, rejim-kırılımı, M3): tanımsal, PASS yetkisiz.

## 19. Effect size / power kriterleri

d ≥ 0.30, power ≥ 0.80 — aynen, değişiklik yok.

## 20. Phase-5 gate'leri (FULL koluna, aynen)

(a) FDR q<0.05; (b) AUC≥0.55 ∧ rank-IC≥0.01 ∧ tau>0; (c) PSS>0 ∧ edge/cost≥1.2;
(d) d≥0.30 ∧ power≥0.80; ardından 3-seed + WF. Eşik değişikliği YOK.

## 21. Incremental edge karar kuralı

PASS iff: FULL §20 zincirini tam geçer VE ΔPSS/Δedge bootstrap CI95 alt
sınırı > 0. Aksi halde **"FUNDING INCREMENTAL EDGE YOK."** (P5 kapalı kalır.)

## 22. Robustness / exploratory ayrımı

- **Robustness (pre-registered, betimsel):** M3-FULL refit; seed 7/123 FULL; WF;
  E032-reprodüksiyon.
- **Exploratory:** L0/L2, ufuk eğrisi, funding × rejim kırılımı (locked
  classifier), settlement-çevresi duyarlılığı (settlement ±1h maskesi, betimsel).
- Exploratory'den PASS/aday çıkmaz.

## 23. Compute budget

Cap 12 CPU-saat. Beklenti: indirme ~dk mertebesi (~3.8k satır), build ihmal,
fitler (3 primary + robustness + 9 WF) <2 CPU-saat. Aşımda SKIP + PARTIAL rapor.

## 24. Reproducibility

Endpoint + istek pencereleri + ham JSON + script sürümleri (phase6b_*) +
seedler + `results6b/` ledger (matrix6b.json, oof6b.parquet, gate6b.json,
manifest6b.json) — 6A artefakt şemasıyla aynı.

## 25. Protected test policy + anti-kontaminasyon

P5/B/C/A'ya load/score/selection YOK. **6A validasyon sonuçları funding
feature/model seçiminde KULLANILMAZ:** feature seti scout primitiflerinden
(§6) 6A sayıları görülmeden donduruldu mantığıyla seçildi; 6A FAIL diye
tasarım optimize edilmedi (5 feature, OPTION'daki aday yönlerle birebir).
6B PASS bile P5'i OTOMATİK açmaz — ayrı M.20 final-test kararı gerekir.

## M.20 onayı olmadan ÇALIŞTIRILAMAZ

İndirme, build, fit, WF, FDR/gate, rapor dahil 6B'ye ait HİÇBİR adım.

**READY FOR M.20 REVIEW** (öneri; onay değil)
