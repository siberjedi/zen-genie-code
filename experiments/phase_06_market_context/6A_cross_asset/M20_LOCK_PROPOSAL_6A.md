# M.20 LOCK PROPOSAL — Phase 6A Cross-Asset (FINAL LOCK CANDIDATE, ONAY YOK)

**Statü:** FINAL LOCK CANDIDATE. M.20 review kararları (M20_REVIEW_6A.md)
işlendi; M.20 ONAYI verilmedi. Onay gelmeden deney çalıştırılmaz,
veri indirilmez, model eğitilmez, backtest yapılmaz, holdout açılmaz.
**Kapsam:** SADECE 6A (cross-asset). 6B dahil değildir.
**Referanslar:** DESIGN_600.md, SOURCE_AUDIT.md, DATA_FEASIBILITY.md,
LEAKAGE_MATRIX.md, EXPERIMENT_OPTIONS.md, PRIORITY_MATRIX.md,
PHASE_06_SCOUT_REPORT.md, DESIGN_500.md, TRAIN_VALIDATION_RESULTS.md,
NIGHT_RUN_REPORT.md, DESIGN_418.md, PROTOCOL.md, config/experiment.yaml.

## 1. Research question

BTC/USDT 5m–1h forward getirileri için cross-asset market context
(breadth, dispersion, correlation regime, BTC-relative strength, ETH/BTC),
OHLCV-only feature setinin (B0–B3) ötesinde **incremental predictive
information** taşıyor mu — locked cost C=0.003 altında ekonomik edge'e
dönüşecek ölçüde?

## 2. H1

FULL kolu (BASE OHLCV + cross-asset), BASE kolundan ekonomik olarak anlamlı
ölçüde ayrışır: ΔPSS = PSS_FULL − PSS_BASE > 0 (bootstrap CI95 alt sınırı > 0,
§21) VE FULL kolu Phase-5 gate zincirini tam geçer (§20).

## 3. H0

Cross-asset context incremental bilgi taşımaz: FULL ile BASE arasında
ekonomik fark yoktur (ΔPSS CI95 sıfırı kapsar ve/veya FULL gate zincirini
geçemez). Sonuç cümlesi: **"CROSS-ASSET INCREMENTAL EDGE YOK."**

## 4. BASE / NEW / FULL ablation (deneyin ana testi)

| Kol | Feature | Label | Model | Seed | Rol |
|-----|---------|-------|-------|------|-----|
| BASE | B3 (28 OHLCV union, frozen) — **E032-verbatim canonical** | L1 | M2 | 42 | Referans (tek tanım, §M20-review-karar-1) |
| NEW | 6 cross-asset feature (§6), BTC OHLCV YOK | L1 | M2 | 42 | Tanısal (tek başına raporlanır, BASE'in yerine geçmez) |
| FULL | B3 + 6 cross-asset | L1 | M2 | 42 | Aday (karar FULL−BASE farkıyla verilir) |

**Canonical BASE kaydı (E032-verbatim):** B3 blok + L1 label + M2 frozen config +
seed 42 + Phase-5 splitleri. Phase 5 ölçümü (TRAIN_VALIDATION_RESULTS.md):
PSS −0.002117, edge/cost −0.706, AUC 0.6811, rank-IC 0.0452, n_train 314571,
n_val 51798, q=1.0. Deneyde aynı konfigürasyon yeniden fit edilir; §9-madde 6
reprodüksiyonu (tolerans 1e-9) geçmeden ilerlenmez.
**E032 vs E014 fark belgesi:** E014 (B1/L1/M2): PSS −0.002069, edge −0.690,
AUC 0.6793, rank-IC 0.0429. Tek fark bloktur (B1 7 feature vs B3 28 union);
label/model/seed/split aynı. Deltalar: Δedge +0.016 (E014 lehine), ΔAUC
−0.0018, ΔrankIC −0.0023 (E032 lehine) — tamamı gürültü mertebesinde, iki hücre
de tüm gate'lerde FAIL (q=1.0, PSS<0). E032 seçildi çünkü: (a) tam OHLCV
bilgisini taşıyan yapısal referans, (b) E014'ü seçmek aynı-VAL seçim yanlılığını
referansa gömerdi. Alternatif elendi, tek tanım kilitlidir.

Ana test = FULL vs BASE incremental karşılaştırma. NEW-only kolu destekleyici;
NEW tek başına geçse bile seçim kriteri değildir. AUC türü istatistiksel
sinyal ile net-after-cost ekonomik edge birbirine karıştırılmaz (§14).

## 5. Asset universe (seçim kuralı + kesin liste önerisi)

**Kural (öneri):** Binance spot USDT pariteleri arasından, (a) 2019-12-31'e
kadar listelenmiş, (b) 2020-01-01 → 2023-06-30 aralığında kesintisiz 5m kline'ı
Vision'da mevcut, (c) 2019 ortalama günlük quote-volume'a göre en likitler,
(d) aynı exchange clock (timestamp integrity).
**Kilitli liste (7, bağlayıcı):** ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, DOGEUSDT,
LTCUSDT, BCHUSDT.
**Bağlayıcı listing/availability kuralı:** bir sembol primary universe'de kalır
iff (a) ilk listeleme ≤ 2019-12-31, (b) Vision'da 2020-01-01 → 2023-06-30
aralığında kesintisiz 5m kline dosyası mevcut (aylık + günlük tamamlama dahil),
(c) 2019 ortalama günlük quote-volume ile majör dilimde. Kuralı bozan sembol
deneyden ÇIKARILIR (ileriye doldurma, geriye uzatma, proxy ikamesi YOK);
çıkarım raporda belgelenir.
**Hariç (kilitli):** SOLUSDT (listeleme 2020-08) ve diğer tüm asset'ler primary
universe'a eklenemez.
**Survivorship notu:** liste 2023H1'e kadar hayatta kalmaya koşullu; hepsi
majör + pencerede delist yok; sınırlılık olarak raporlanır. Delist/duraklama
tespit edilirse o sembol düşürülür (ileriye doldurma YOK).

## 6. Feature family'leri (6 adet, şişirme yok)

Grid: BTC 5m close zamanları. `r(a,k,t) = close_a(t)/close_a(t−k) − 1`
(hizalanmış gridde; eksik bar → satır düşer).

- **F1 breadth_1:** `mean_a 1[r(a,1,t) > 0]` (5m breadth)
- **F2 breadth_12:** `mean_a 1[r(a,12,t) > 0]` (1h breadth)
- **F3 dispersion_12:** `std_a r(a,12,t)` (1h cross-sectional yayılım)
- **F4 btc_rel_12:** `r(BTC,12,t) − mean_a r(a,12,t)` (BTC-relative strength)
- **F5 ethbtc_chg_12:** `[ETH(t)/BTC(t)] / [ETH(t−12)/BTC(t−12)] − 1`
- **F6 corr_regime:** trailing 288 bar 5m returnleriyle 21 parite
  korelasyonunun ortalaması (1-günlük bağlılık rejimi)

Tümü trailing-only; BTC-öz momentum ailesi YOK (B0'da var).

## 7. Feature formülleri

§6'daki tanımlar bağlayıcıdır. Ek detay: korelasyon Pearson, min_periods=288
(eksikse NaN → satır düşer); breadth/dispersion eşit-ağırlıklı; fiyatlar
adj-close yok (spot, temettü/bölünme yok); ETH/BTC oranı ham close'larla.

## 8. Timestamp / availability / candle-close kuralları

- Karar anı: BTC 5m bar close `t`. Her cross-asset değer yalnızca
  `close_time ≤ t` barlarından türetilir (LEAKAGE_MATRIX A1).
- Sembol barı eksikse o `t` satırı düşürülür (dropna politikası, Phase 5 ile aynı).
- Aylık Vision dosyaları tarihsel olduğundan availability sorunu yoktur;
  kural yalnızca bar-hizalaması içindir.

## 9. Leakage kontrolleri (pre-registered checklist)

1. `.shift(-n)` / centered rolling / ileri-fill kaynak taraması (causality probe).
2. Feature[t] yalnızca close_time ≤ t barları (unit test: sentetik ileri-bar).
3. Eksik-bar düşürme oranı raporu (sembol başına).
4. BTC-öz momentum sızıntısı: NEW kolunda BTC serisi kullanılmadığı assert edilir.
5. Universe listeleme-tarih kanıtı (Vision dosya mevcutluğu).
6. Reprodüksiyon: BASE kolu E032 skorunu seed-42'de yeniden üretmeli
   (tolerans 1e-9; üretemezse STOP — pipeline hatası).

## 10. Label ve horizon

- **Primary:** L1 (Y > C, H=12 → 1h), Phase 5'in tek bilgilendirici kolu.
  Primary scope YALNIZCA 5m → 1h; 15m → 3h secondary bu lock'tan ÇIKARILDI,
  yeni secondary family AÇILMAZ.
- **Exploratory (gatesiz):** L0/L2, ufuklar 3/36/72 (5m grid).
- Label tanımı/off-by-one/label-bound Phase 5 ile birebir aynı.

## 11. Train / Validation / protected holdout

- TRAIN 2020-01-01 → 2022-12-31; VAL 2023-01-01 → 2023-06-30 (Phase 5 ile aynı).
- **KİLİTLİ:** FINAL_P5=2025H1, Final B=2024H1, Final C=2024H2, Final A=2023H2
  (tüketildi). 6A VAL-gated'dır; P5 gelecekteki final test için rezerve kalır.
- Veri indirme planı 2023-06-30 sonrasını KAPSAMAZ (NO 2025H1 DOWNLOAD).

## 12. Frozen model ailesi

**Primary decision model: M2 tek model** (RF: n_estimators=200, max_depth=8,
min_samples_leaf=50, class_weight=balanced, n_jobs=1, seed=42) — Phase 5 frozen
config verbatim. LR/Ridge (M1) ve LGBM (M3) primary decision familyasına DAHİL
DEĞİL; M3-FULL refit yalnızca robustness (§22) kapsamında betimsel raporlanır,
PASS/FAIL kararına etki etmez. Model araması Phase 5'te kapandı, yeniden açılmaz.

## 13. Hyperparameter tuning kuralları

**TUNING YOK.** Tüm konfigürasyonlar Phase 5 değerleriyle verbatim frozen.
Tuning'e kalkışmak protokol ihlalidir (Madde 10/20).

## 14. Primary metric

FULL kolu PSS ve edge/cost (Phase 5 tanımıyla) + §21 incremental kuralı.
İstatistiksel sinyal (AUC ~0.6x) ekonomik edge yerine geçemez:
AUC tek başına PASS üretemez.

## 15. Secondary metrics

AUC, PR-AUC, logloss, Brier, ECE, dir-acc, rank-IC, Kendall tau, Cohen d,
power, Welch CI, decile tablosu — 3 kol için de raporlanır, gate üretmez.

## 16. Transaction cost / friction

C = 0.003 locked (fee 0.001×2 + slip 5bps×2). Değişiklik yok. Haber-anı
çarpanı bu deneyde uygulanmaz (haber verisi yok).

## 17. Statistical tests

Phase 5 makinesi birebir: top-decile one-sample t-test (H0: mean ≤ C) →
tek primary BH-FDR ailesi (3 test: BASE/NEW/FULL, α=0.05); ΔPSS için
percentile bootstrap CI95 (10k resample, seed 42); adayda 3-seed
sign-consistency (42/7/123, ≥2/3) + walk-forward (365/90/90/90,
expanding=false, ~9 fold, tutarlılık ≥0.60, fold overlap notuyla).

## 18. FDR family yapısı

- **Primary family (PASS yetkili, TEK familya):** {BASE, NEW, FULL} 5m/H12/L1/M2 = 3 test.
- Aile dışı (L0/L2, ufuklar, M3-refit): tanımsal, FDR dışı, PASS yetkisiz.

## 19. Effect size / power kriterleri

d ≥ 0.30 (top vs bottom decile), power ≥ 0.80 — Phase 5 ile aynı, değişiklik yok.

## 20. Phase 5'ten devralınan gate'ler (FULL koluna, aynen)

(a) FDR q<0.05; (b) destek AUC≥0.55 ∧ rank-IC≥0.01 ∧ tau>0;
(c) PSS>0 ∧ edge/cost≥1.2; (d) d≥0.30 ∧ power≥0.80; ardından 3-seed + WF.
Eşik değerlerinde değişiklik YOK.

## 21. Incremental edge karar kuralı (KİLİTLİ — review kararı 4)

Ana karşılaştırma FULL − BASE. Primary incremental criterion: ΔPSS ve
Δedge/cost için bootstrap %95 CI alt sınırı > 0 (10k resample, seed 42).
PASS iff: FULL §20 zincirini tam geçer VE ΔCI alt sınırı > 0.
CI sıfırı içeriyorsa incremental edge PASS sayılmaz. AUC tek başına PASS
üretemez. Aksi halde **"CROSS-ASSET INCREMENTAL EDGE YOK"** (A-benzeri
kapanış; P5 kapalı kalır).

## 22. Robustness / exploratory ayrımı

- **Robustness (pre-registered, betimsel):** M3-FULL refit; seed 7/123 FULL;
  WF; E032-reprodüksiyon (§9-madde 6).
- **Exploratory (sonuç fishing'i değil):** L0/L2, ufuk eğrisi (3/36/72),
  sembol-düşürme duyarlılığı (leave-one-asset-out, betimsel).
- Exploratory'den PASS/aday çıkmaz.

## 23. Compute budget

Cap 12 CPU-saat (Phase 5 emsali). Beklenti: indirme <0.5h duvar, feature build
<1 CPU-saat, fitler (3 primary + ~4 robustness + 9 WF) <3 CPU-saat. Toplam
<5 CPU-saat. Aşımda kalan iş SKIP + PARTIAL rapor (karar E-benzeri).

## 24. Reproducibility

Vision URL + checksum listesi, script sürümleri (phase6a_*), seedler, ham
yanıtlar, `results6a/` ledger (matrix6a.json, oof6a.parquet, gate6a.json,
manifest6a.json) — Phase 5 artefakt şemasıyla aynı.

## 25. Protected test policy

VAL-gated deney; P5/B/C/A'ya load/score/selection YOK. P5 (2025H1), gelecekteki
nihai final test adayı olarak rezerve kalır; 6A PASS bile P5'i OTOMATİK açmaz —
ayrı M.20 final-test kararı gerekir (Madde 2/3/4). Final A tüketildi,
tekrar kullanılmaz.

## Review kararları (M20_REVIEW_6A.md — 5/5 resolved, onay pending)

1. BASE = E032-verbatim canonical (fark belgesi §4'te).
2. Universe = 7 sembol kilitli; SOL+diğerleri primary dışı; listing kuralı §5'te.
3. Primary model = M2 tek; M1/M3 primary dışı (M3 yalnızca robustness).
4. Incremental criterion = ΔCI95 alt > 0 (kilitli); CI sıfırı içerirse PASS yok.
5. 15m secondary çıkarıldı; scope 5m → 1h tek.

## M.20 onayı olmadan ÇALIŞTIRILAMAZ

Veri indirme, feature build, model fit, WF, FDR/gate hesabı, rapor üretimi dahil
6A'ya ait HİÇBİR adım. M20_DECISION_6A.md bu otoriteye aittir; bu belge FINAL
LOCK CANDIDATE'tir, onay değildir.

**READY FOR FINAL M.20 APPROVAL**
