# M.20 LOCK PROPOSAL — Phase 6C Open Interest (TASLAK, ONAY YOK)

**Statü:** ÖNERİ. M.20 onayı verilmedi; onay gelmeden deney çalıştırılmaz,
veri indirilmez, model eğitilmez, backtest yapılmaz, holdout açılmaz.
**Kapsam:** SADECE 6C (OI). 6A/6B sonuçları değiştirilmez; 6A/6B dosyalarına
dokunulmaz.
**Referanslar:** 6C scout (SOURCE_AUDIT_6C, DATA_FEASIBILITY_6C,
LEAKAGE_ASSESSMENT_6C, EXPERIMENT_OPTION_6C, PHASE_06C_SCOUT_REPORT,
feasibility_6c.json), 6A/6B lock-review-run-results, DESIGN_500,
TRAIN_VALIDATION_RESULTS, DESIGN_418, PROTOCOL.md, config/experiment.yaml.

## 1. Research question

BTCUSDT perpetual Open Interest akışı (değişim, z-score, price-OI
divergence), BTC'nin kendi OHLCV bilgisine eklenince maliyet sonrası
out-of-sample incremental edge sağlıyor mu? (5m grid, 1h forward, C=0.003.)

## 2. H1

FULL kolu (BASE OHLCV + OI), BASE kolundan ekonomik olarak anlamlı ölçüde
ayrışır: ΔPSS > 0 (bootstrap CI95 alt sınırı > 0, §21) VE FULL Phase-5 gate
zincirini tam geçer (§20).

## 3. H0

OI incremental bilgi taşımaz (ΔPSS CI95 sıfırı kapsar ve/veya FULL gate
zincirini geçemez). Sonuç cümlesi: **"OI INCREMENTAL EDGE YOK."**

## 4. BASE / NEW / FULL ablation (deneyin ana testi)

| Kol | Feature | Label | Model | Seed | Rol |
|-----|---------|-------|-------|------|-----|
| BASE | B3 (28 OHLCV union, frozen) — **E032-verbatim canonical** (6A/6B ile aynı) | L1 | M2 | 42 | Referans |
| NEW | 5 OI feature (§6), BTC OHLCV YOK | L1 | M2 | 42 | Tanısal (tek başına raporlanır, BASE'in yerine geçmez) |
| FULL | B3 + 5 OI | L1 | M2 | 42 | Aday (karar FULL−BASE farkıyla verilir) |

Ana test = FULL vs BASE. AUC türü sinyal ile ekonomik edge karıştırılmaz (§14).

## 5. Venue / sembol

Tek kaynak (kilitli): **Binance USDⓈ-M BTCUSDT perpetual**,
`data/futures/um/daily/metrics/BTCUSDT/` (resmi Vision arşivi).
Gerekçe: hedef varlıkla aynı venue/sembol, flagship kontrat (2019-09+,
kesintisiz). COIN-M veya başka sembol eklenemez.

## 6. Exact OI feature set (5 adet)

Ham kolonlar (kilitli): `create_time`, `sum_open_interest` (BTC adedi).
(`sum_open_interest_value` kullanılmaz — value/coins ≈ mark-price proxy,
BTC close ile redundant.) Oran kolonları (long/short) kullanılmaz
(2022-Q1 gap + bu deneyin sorusu OI akışı).
Grid: BTC 5m close zamanları; `OI(t)` = `create_time ≤ t` son snapshot (§8).

- **F1 oi_chg_12:** `(OI(t) − OI(t−12)) / OI(t−12)` (1h akış; lookback 12 bar).
- **F2 oi_z_288:** `(OI(t) − mean_288) / std_288(ddof=1, min_periods=288)`
  (1-günlük konumlanma aşırılığı; lookback 288 bar).
- **F3 oi_price_div:** `sign(r_btc_12(t)) × sign(oi_chg_12(t))` →
  +1 aynı-yön, −1 divergence, 0 (ikisi de sıfırsa). r_btc_12 BTC close'tan.
- **F4 oi_chg_1:** `(OI(t) − OI(t−1)) / OI(t−1)` (5m ani akış; lookback 1 bar).
- **F5 oi_range_288:** `(OI(t) − min_288) / (max_288 − min_288)` (1-günlük
  bant konumu; max==min ise 0.5 — flat-gün disambiguation, raporda notlu).

Tümü trailing-only. Payda sıfır olamaz (OI>0 assert'li); sıfır bölme → NaN →
satır düşer (icat değer yok, F5 kuralı hariç — o da kilitli sabit).

## 7. Formül ek detayları

§6 bağlayıcıdır. std ddof=1 (M2 monoton-duyarsız, 6A §7 emsali).
Pencereler mum-endekslidir (settlement-endeksi DEĞİL — OI sürekli seridir,
funding §7'den farklı). min_periods = pencere boyu (kısa pencere doldurulmaz).

## 8. Timestamp / availability / candle-close kuralları

- Karar anı `t` (5m close) yalnızca `create_time ≤ t` snapshot'ları
  (merge_asof backward, exact-ms, yuvarlama yok).
- Bar-içi türev istatistik (bar-içi OI max vb.) feature OLAMAZ.

## 9. Geceyarısı dedup kuralı (exact, deterministik)

Günlük dosyalar `D 00:05 → D+1 ~00:00:02` aralığını kapsar; geceyarısı bucket'ı
iki dosyada görünür. Kural (kilitli): dosyalar gün-sırasıyla birleştirilir,
`create_time`'a göre sıralanır, `drop_duplicates(subset=create_time,
keep='first')` uygulanır (erken-gün dosyası kazanır). Dedup sonrası kalan dup
`create_time` → STOP. Kural değişikliği = lock değişikliği.

## 10. Leakage kontrolleri (pre-registered checklist)

1. Causality probe (`.shift(-`, centered rolling, ileri-fill taraması).
2. Feature[t] yalnızca `create_time ≤ t` snapshot'ları (unit test: sentetik ileri-snapshot).
3. Dedup determinizmi testi (sentetik çift-yazım).
4. NEW-kolon = 5 kilitli familya; B0–B3 blok kolonu yok (assert).
5. İlk OI tarihi ≤ 2020-09-30 kanıtı (coverage; §11).
6. BASE E032-reprodüksiyon (tol 1e-9; tutmazsa STOP).

## 11. Train data loss kabul/red kriteri (kilitli)

OI ~2020-09-10 başlar → FULL train satırları OI-yok aralıkta DÜŞER
(tahmini ~%30 train kaybı; VAL tam kalır — VAL'de boşluk STOP sebebidir).
**Kabul:** FULL `n_train ≥ 200.000` VE `n_val == BASE n_val` (VAL kaybı sıfır).
Sağlanmazsa STOP + blocker raporu (fallback YOK, split DEĞİŞMEZ).
Kayıp satır aralıkları raporda belgelenir.

## 12. Label ve horizon

**Primary:** L1 (Y > C, H=12 → 1h), 5m grid. Scope YALNIZCA 5m → 1h; ikincil
familya YOK. **Exploratory (gatesiz):** L0/L2, ufuk eğrisi 3/36/72
(FULL-L1 skorları sabit).
Label tanımı/off-by-one/label-bound Phase 5 ile birebir aynı.

## 13. Train / Validation / protected holdout

TRAIN 2020-01-01 → 2022-12-31; VAL 2023-01-01 → 2023-06-30 (değişmez).
**KİLİTLİ:** FINAL_P5=2025H1, Final B=2024H1, Final C=2024H2, Final A=2023H2
(tüketildi). 6C VAL-gated; P5 rezerve. İndirme 2020-01-01 → 2023-06-30'u
kapsar, sonrasını KAPSAMAZ.

## 14. Frozen model ailesi

**Primary: M2 tek model** (RF 200/8/50/balanced/n_jobs=1, seed 42, verbatim).
M1/M3 primary dışı; M3-FULL refit yalnızca betimsel robustness (§22).

## 15. Hyperparameter tuning kuralları

**TUNING YOK.** İhlal = protokol ihlali (Madde 10/20).

## 16. Primary metric

FULL PSS + edge/cost (§21 incremental kuralıyla). AUC tek başına PASS üretemez.

## 17. Secondary metrics

AUC, PR-AUC, logloss, Brier, ECE, dir-acc, rank-IC, Kendall tau, Cohen d,
power, Welch CI, decile tablosu — 3 kol için raporlanır, gate üretmez.

## 18. Transaction cost / friction

C = 0.003 locked. Değişiklik yok.

## 19. Statistical tests

6A/6B makinesi birebir: top-decile one-sample t-test (H0: mean ≤ C) → tek
primary BH-FDR ailesi (3 test, α=0.05); ΔPSS/Δedge paired percentile bootstrap
CI95 (10k resample, seed 42); adayda 3-seed sign-consistency (42/7/123, ≥2/3) +
WF (365/90/90/90, expanding=false, ~9 fold, ≥0.60, overlap notuyla).

## 20. FDR / effect / power

Tek primary familya; d ≥ 0.30, power ≥ 0.80 — aynen, değişiklik yok.

## 21. Phase-5 gate'leri + incremental kural (FULL koluna, aynen)

(a) FDR q<0.05; (b) AUC≥0.55 ∧ rank-IC≥0.01 ∧ tau>0; (c) PSS>0 ∧ edge/cost≥1.2;
(d) d≥0.30 ∧ power≥0.80; ardından 3-seed + WF. PASS iff zincir tam + ΔCI95
alt sınırı > 0. Aksi halde **"OI INCREMENTAL EDGE YOK."** (P5 kapalı kalır.)

## 22. Robustness / exploratory ayrımı

- **Robustness (pre-registered, betimsel):** M3-FULL refit; seed 7/123 FULL; WF;
  E032-reprodüksiyon.
- **Exploratory:** L0/L2, ufuk eğrisi, OI × rejim betimsel kırılımı (locked
  classifier kuralı, native fallback, 6B §22 emsali).
- Exploratory'den PASS/aday çıkmaz.

## 23. Fallback (kilitli)

Ücretli kaynaklar (Tardis/CoinGlass) primary pipeline'a GİRMEZ. S1 run-time
teyidi çökerse deney STOP eder; fallback ayrı M.20 kararı gerektirir (bu
lock'ta kapsam dışı).

## 24. Compute budget + reproducibility

Cap 12 CPU-saat; beklenti <3 CPU-saat (MB'lar indirme). Vision URL + checksum
listesi, script sürümleri (phase6c_*), seedler, `results6c/` ledger
(matrix6c.json, oof6c.parquet, gate6c.json, manifest6c.json) — 6A/6B şemasıyla aynı.

## 25. Protected test policy + anti-kontaminasyon

P5/B/C/A'ya load/score/selection YOK. **6A/6B sonuçları OI feature seçiminde
KULLANILMAZ:** set scout primitiflerinden (değişim/z-score/divergence) geldi;
6A/6B FAIL diye optimize edilmedi. 6C PASS bile P5'i OTOMATİK açmaz.

## M.20 onayı olmadan ÇALIŞTIRILAMAZ

İndirme, build, fit, WF, FDR/gate, rapor dahil 6C'ye ait HİÇBİR adım.

**READY FOR M.20 REVIEW** (öneri; onay değil)
