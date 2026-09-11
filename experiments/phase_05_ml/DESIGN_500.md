# PHASE 5 — ML SİNYAL ARAŞTIRMASI (phase_05_ml)
## DESIGN-ONLY / PREREGISTRATION — 2026-09-07

> Statü: **TASARIM + M.20 FORMALIZED (2026-09-07)**. NO CODE · NO TRAINING ·
> NO TUNING · NO BACKTEST · NO FINAL TEST EVALUATION · NO PROTOCOL LOCK CHANGE.
> RL hattı Phase 4.19 kararıyla STOP edildi; bu belge yeni hattın ön-kaydıdır.
> M.20 kararları user tarafından verilmiş ve `M20_FORMALIZATION_2026-09-07.md`'ye
> kaydedilmiştir (holdout=2025H1; B/C korunur; threshold paketi korunur; 4 FDR ailesi;
> argmax rule). Resmî M.20 protokol kilidi + 2025H1 indirme onayı user'ındadır;
> bu kayıt onaylanmadan deney pipeline'ı çalıştırılmaz.

---

## 1. RESEARCH QUESTION

> OHLCV'den türetilen, yalnızca t anına kadar bilgi kullanan özellikler,
> **işlem maliyetleri (fee + slippage) dikkate alındığında**, gelecekteki getiriyi
> tahmin eden **gerçek ve tekrarlanabilir** bir sinyal taşıyor mu?

- Bu fazın amacı BOT DEĞİL, **sinyal**dır. Karar katmanları:
  a) predictive signal var mı (İSTATİSTİKSEL) →
  b) sinyal maliyeti karşılıyor mu (EKONOMİK) →
  c) ancak (a)+(b) sağlanırsa ayrı, onaylı bir tasarımda trading strategy/backtest.
- RL (Phase 4) karar-düzeyi edge göstermedi; RL başarısızlığı ML'nin başarısızlığı
  anlamına gelmez (PROTOCOL FAZ 5 mantığı). Ancak RL'nin **maliyet bulgusu**
  devralınır: 5m'de round-trip ≈ %0.30 → bu fazın ekonomik filtresi cost-aware'dir.

## 2. HYPOTHESES

- **H1 (ana)**: En az bir label kolunda (L0/L1/L2), frozen matriste en az bir
  feature block × model hücresi, validation OOS'ta hem istatistiksel sinyal
  hem cost-aware ekonomik üstünlük gösterir (bölüm 12 kriterleri).
- **H1a (yardımcı)**: Tahmin edilen olasılık/değer artıkça gerçekleşen future
  return monoton artar (decile ayrışması; high-confidence bucket > low-confidence).
- **H1b**: Candle-structure feature blokları (B2: BODY/WICK/close-position —
  Phase 4 RL'de hiç bulunmayan aile) tek başına sinyale katkı verir (B2 hücreleri).
- **H2 (keşifsel, başarı kanıtı DEĞİL)**: TF farklılaşması — 15m→3h blok
  (bölüm 15) aynı maliyetle farklı sinyal verir mi?

## 3. NULL HYPOTHESIS

- **H0**: H1 için seçilen label kolunda, tüm frozen hücrelerin validation OOS
  sinyal istatistiği, trend-aware (drift) / majority (mean) baseline'ından ve
  maliyet eşiğinden anlamlı şekilde ayrışmaz → **PHASE 5 FAIL / STOP**
  (bölüm 16/22). "AUC 0.55'te 'başardık'" DENMEZ; anlamlı ama net-negatif
  expected return = NO ECONOMIC EDGE = FAIL (user kuralı, bölüm 11).

## 4. DATASET

- **Sembol:** BTC/USDT (tek-pair; multi-pair B10 gerektirmez; PROTOCOL değişmez).
- **Birincil TF:** 5m. Kaynak: `freqtrade/user_data/data/binance/BTC_USDT-5m.feather`
  (mevcut, indirilmez). Doğrulandı: **420,014 satır, 2020-01-01 → 2023-12-30 23:55 UTC**,
  kolonlar `date, open, high, low, close, volume` — OHLC mevcuttur ve candle-structure
  feature'ları için gereklidir.
- **İkincil TF (keşifsel):** 15m — yalnızca 5m feather'dan **tamamlanmış bar**
  resample'ı (`open=first, high=max, low=min, close=last, volume=sum`; kısmi son bar
  DÜŞER; nedensel, indirme yok). 1h→6h: bu turda YOK (bölüm 15).
- Sıfır hacimli mumlar mevcuttur; `vol_*` feature'ları bölme için küçük epsilon
  kullanır veya NaN bırakır (doldurma yok, düşürme var). NaN politikası bölüm 8.

## 5. TRAIN / VALIDATION / FINAL SPLIT

| Pencere | Aralık | Rol | Yerel veri |
|---|---|---|---|
| TRAIN | 2020-01-01 → 2022-12-31 | model fit | ✔ feather içinde |
| VALIDATION | 2023-01-01 → 2023-06-30 | **tüm seçim** (frozen matrix, decile, feature/model/label kanıtı) | ✔ |
| FINAL (Phase 5 holdout) | **2025-01-01 → 2025-06-30 (M.20 karar taslağı)** | tek kez, yalnızca seçilen model+label+block | ✘ 2025H1 indirme gerekir (uygulamada, ayrı onay) |

- **"Final Test A" adı çakışması [KRİTİK PROTOKOL NOTU]:** `config/experiment.yaml`
  ve `src/freqai/splits.py`'da **Final Test A = 2023-07-01→2023-12-31** FreqAI'nin
  kilitli final penceresidir ve **Phase 3 tarafından TÜKETİLMİŞTİR**
  (`results/final_test_a_trades.csv` + RESULT_2026-09-04 hash kaydı). Anayasa
  Madde 3/4: bir fazın final testi başka fazın tasarımında KULLANILAMAZ; kullanılırsa
  yeni final gerekir. Bu yüzden Phase 5, 2023H2'yi final olarak SAHİPLENEMEZ.
- **Holdout kararı (M.20 karar taslağı — 2026-09-07, user seçimi):** **YENİ
  DOKUNULMAMIŞ PENCERE = 2025-01-01 → 2025-06-30 (2025H1)** (seçenek B — Final
  A/B/C pencereleriyle çakışmaz, VAL sonrası bağımsız bir OOS yılı).
  - **Final Test B** (2024-01-01→2024-06-30, RL'e ayrılmış, env guard'lı,
    TÜKETİLMEMİŞ) ve **Final Test C** (2024-07-01→2024-12-31, FAZ-5 karşılaştırma)
    **KORUNUR**; Phase 5 tarafından kullanılmaz. Tek gözlemi hem RL-B hem ML-Final
    yapmak, karşılaştırma gününde pencereyi tarafsız hakemlikten çıkarır ve RL'nin
    temiz final seçeneğini kapatır (M.20 review nota — ben LOCK ETMIYORUM).
  - Yeni pencere → uygulamada **2025H1 veri indirme GEREKLİ**; indirme, tüm seçim
    kararları (matris/gate/aday) hash-lock edildikten SONRA açılır (guard, bölüm 8/18)
    ve TEK KEZ değerlendirilir. **İndirme bu turda YOK** (ayrı onay).
  - **`REQUIRES M.20 PROTOCOL APPROVAL`**: split tablosuna yeni rezervasyon
    (FINAL_TEST_P5 / 2025H1) + indirme onayı.
- Final pencere sonuçlarına bakılarak hiçbir karar alınmaz; yalnızca raporlanır.

## 6. LABEL DEFINITIONS

- **Y(t) = future_return(t, H) = close[t+H]/close[t] − 1**, H mum ileride.
  Base = `close[t]`; forward aralık **`t+1 .. t+H`** (base mum forward'ta DEĞİL —
  off-by-one guard, bölüm 8).
- **Cost model (kilitli parametrelerden):**
  `C = 2 × (fee 0.001 + slippage 0.0005) = 0.003 (%0.30)` round-trip.
  Phase 3'ün eski label eşiği 0.002 (yalnız fee) idi; **Phase 5 L1 eşiği TAM
  yuvarlak maliyettir (0.003)** — RL kayıtları ve Phase 4.18 drift (1h ≈ +0.0154%)
  ile tutarlı, ekonomik olarak anlamlı filtre.

| Label id | Tip | Tanım | Kullanım |
|---|---|---|---|
| **L0** | binary direction | `Y(t) > 0` | ham yön sinyali (istatistiksel üst sınır) |
| **L1** | cost-aware direction | `Y(t) > C` (C=0.003) | ekonomik sinyal — birincil ekonomik kol |
| **L2** | regression | `Y(t)` (devamlı) | getiri regresyonu; maliyet sonrası bucket-premium'da uygulanır |

- Label'lar tuning ile seçilmez; **üçü ayrı, önceden tanımlı deney kolu**dur.
  Son üç satır label'ı tanımsızdır (drop), mekanik.
- Sınıf dengesi: `class_weight="balanced"` (Phase 3 convention'ı, fiyat-duyarlı)
  sadece ağaç/lojistik sınıflandırıcılarda; gerçek pozitif oranı raporlanır,
  eşiğe göre AYARLANMAZ.

## 7. FEATURE FAMILIES (yalnızca geçmiş OHLCV)

Feature kataloğu tek UNION olarak kilitlenir; `B0/B1/B2` blokları bu union'ın
önceden tanımlı bölümleridir (ablasyon, "family selection" DEĞİL). Tüm pencereler
geriye dönüktür, satır i yalnızca mum ≤ i bilgisi görür.

| Family | Feature | Formül / pencere |
|---|---|---|
| A) Returns | `ret_1` `ret_3` `ret_12` `ret_36` `ret_72` | `close.pct_change(k)`, k∈{1,3,12,36,72} |
| B) Trend | `sma50_ratio` | `close/SMA50 − 1` (50) |
| | `sma200_ratio` | `close/SMA200 − 1` (200) |
| | `ema12_ratio` | `close/EMA12 − 1` |
| | `ema26_ratio` | `close/EMA26 − 1` |
| | `sma_trend` | `(SMA50 > SMA200)` |
| | `sma50_slope` | `(SMA50_t / SMA50_{t−12}) − 1` |
| C) Momentum | `rsi14` | Wilder RSI(14) (Phase 3 aynı fonksiyon) |
| | `roc_36` | `close/close_{t−36} − 1` |
| | `ema_diff_12_26` | `(EMA12 − EMA26)/close` |
| D) Volatility | `atr14_ratio` | Wilder ATR(14)/close (Phase 3 aynı fonksiyon) |
| | `roll_std_24_ratio` | `close.rolling(24).std()/close` |
| | `rv_12` | `ret_1.rolling(12).std() × sqrt(288×365)` (yıllıklaştırılmış RV) |
| | `vol_percentile_1d` | trailing 288-mum percentile rank of `roll_std_24` (nedensel) |
| E) Volume | `vol_z` | `volume/trail_mean24 − 1` (Phase 3 aynı) |
| | `vol_change` | `volume_t/volume_{t−1} − 1` |
| | `vol_ratio_168` | `volume/trail_mean168 − 1` (1 hafta) |
| F) Candle structure *(RL'de YOK)* | `body_ratio` | `|close−open|/range` |
| | `up_wick_ratio` | `(high − max(open,close))/range` |
| | `low_wick_ratio` | `(min(open,close) − low)/range` |
| | `close_pos` | `(close − low)/range` — close'un range içindeki pozisyonu |
| | `range_pct` | `range/close` |
| G) Regime | `adx14_ratio` | Wilder ADX(14)/100 (mekanik, lock'lu classifier ile aynı matematik) |
| | `vol_rank_288` | trailing percentile rank of ATR(14) (288 mum, nedensel) |

**Frozen blocks:**
- **B0 = "base"** (A+B+E): `ret_1,ret_3,ret_12,ret_36,ret_72, sma50_ratio, sma200_ratio,
  ema12_ratio, ema26_ratio, sma_trend, sma50_slope, vol_z, vol_change, vol_ratio_168` (14)
- **B1 = "momentum+vol"** (C+D): `rsi14, roc_36, ema_diff_12_26, atr14_ratio,
  roll_std_24_ratio, rv_12, vol_percentile_1d` (7)
- **B2 = "candle+regime"** (F+G): `body_ratio, up_wick_ratio, low_wick_ratio,
  close_pos, range_pct, adx14_ratio, vol_rank_288` (7) — **RL'de hiç görülmemiş aile**
- **B3 = full**: B0∪B1∪B2 (28 feature)

Not: time-of-day / saat dilimi bu turda DIŞI (yalnızca OHLCV kuralı). Feature
ablasyonu ek scoring'a evrilmez; B0/B1/B2 hücreleri tek başına kanıt taşır (H1b).

## 8. LEAKAGE CONTROLS

- **Nedensellik:** her `feature[t]` yalnızca mum ≤ t bilgisiyle hesaplanır.
  Yasak: `.shift(-n)`, centered rolling, ileriye dönük fill, gelecek mum.
- **Candle/execution hizası (AÇIKÇA DOKÜMANTE):**
  1. `t` = karar anında **son kapanan mum**. Candle `t`'nin OHLCV'si o kapanışta
     TAMAMEN bilinir → `feature[t]` gövde/fitil bilgisini kullanabilir (Phase 3
     konvansiyonu; Phase 4.18 audit'teki obs-penceresi +1 mum farkıdır, bilgi
     taşmaz çünkü candle `t` kapandığında karar verilir).
  2. **Execution = close[t]** (sinyal anı = karar anı; slippage ayrıca maliyette).
  3. **Forward penceresi = `t+1 .. t+H`** — base candle `t` ASLA forward aralığa
     girmez (off-by-one guard; Phase 4.15/4.18 audit semantiği, r_h uyumlu).
- **Label/feature ayrımı:** feature'lar label'dan bağımsız üretilir
  (`build_features` → `build_labels` → join; Phase 3 `splits.build_dataset` aynı
  düzen, test kanıtlı).
- **Warmup:** en uzun pencere SMA200/EMA26 (199) + label kuyruğu (12/H) → mekanik
  drop (Phase 3 `expected_dropped`: 199 + H). Resample 15m'de warmup BAR sayısını
  değiştirir ama aynı hesap korunur (dokümante).
- **Normalizasyon (yalnızca doğrusal model M1):** StandardScaler SADECE TRAIN'e
  fit edilir, val'e yalnızca uygulanır; scaler istatistikleri artefakta saklanır.
  RF/LGBM ölçeklenmez (Phase 3 convention'ı).
- **Walk-forward kırılımı:** fold'lar bağımsız DEĞİLDİR (overlap, Anayasa Madde 8);
  yön-gösterge olarak raporlanır (bölüm 13).
- **Final protect:** her loader, (i) FINAL penceresine dokunmayı (ii) VAL sonrası
  veriyi kullanmayı ABORT'layan guard çağırır (`assert_no_final_leak` mantığı,
  FINAL_END parametreli). Hiçbir seçim script'i final penceresine referans içermez.

## 9. MODEL SET (frozen, toplam 3 + baseline)

| Model | L0/L1 (classification) | L2 (regression) | Frozen hiperparametreler |
|---|---|---|---|
| **M1 LR/Ridge** | sklearn LogisticRegression | sklearn Ridge | `C=1.0, penalty=l2, solver=lbfgs, max_iter=1000, class_weight=balanced` / `alpha=1.0`; StandardScaler yalnızca M1'e (train-fit) |
| **M2 RF** | RandomForestClassifier | RandomForestRegressor | **Phase 3 kilitli config:** `n_estimators=200, max_depth=8, min_samples_leaf=50, class_weight=balanced, n_jobs=1` (gerekçe: protokol-içi süreklilik) |
| **M3 LGBM** | LGBMClassifier | LGBMRegressor | `n_estimators=500, learning_rate=0.05, num_leaves=31, colsample_bytree=0.8, subsample=0.8, verbosity=-1` (frozen); LightGBM kurulu değilse M.20 onayıyla XGBoost yerine geçer |
| **BASE** | Majority-class | mean(Y) | feature-use YOK — her label kolunda 1 cell |

- Model/feature/hiperparametre/seed seçimi SADECE Train+Validation (PROTOCOL).
- **Tuning bütçesi:** bu turda hücre-başı hiperparametre tuning'i YOK — her model
  yukarıdaki frozen varsayılanla koşar. Hiperparametre tuning, ancak sinyal
  geçerse VE ayrı ön-kayıtlı aşamada (yine yalnızca Train+Validation) açılır.

## 10. EXPERIMENT MATRIX (DONDURULMUŞ)

Birincil matris (5m → h=12=1h, validation OOS, her cell = 1 train-fit + 1 val-predict + metrik):

| ID | Blok | Label | Model | Ufuk (birincil h=12) | Seçim kuralı | Validation rolü |
|---|---|---|---|---|---|---|
| E001 | B0 | L0 | M1 | 12 | frozen, rapor | kanıt |
| E002 | B0 | L0 | M2 | 12 | frozen, rapor | kanıt |
| E003 | B0 | L0 | M3 | 12 | frozen, rapor | kanıt |
| E004 | B0 | L1 | M1 | 12 | frozen, rapor | kanıt |
| E005 | B0 | L1 | M2 | 12 | frozen, rapor | kanıt |
| E006 | B0 | L1 | M3 | 12 | frozen, rapor | kanıt |
| E007 | B0 | L2 | M1 | 12 | frozen, rapor | kanıt |
| E008 | B0 | L2 | M2 | 12 | frozen, rapor | kanıt |
| E009 | B0 | L2 | M3 | 12 | frozen, rapor | kanıt |
| E010 | B1 | L0 | M1 | 12 | frozen, rapor | kanıt |
| E011 | B1 | L0 | M2 | 12 | frozen, rapor | kanıt |
| E012 | B1 | L0 | M3 | 12 | frozen, rapor | kanıt |
| E013 | B1 | L1 | M1 | 12 | frozen, rapor | kanıt |
| E014 | B1 | L1 | M2 | 12 | frozen, rapor | kanıt |
| E015 | B1 | L1 | M3 | 12 | frozen, rapor | kanıt |
| E016 | B1 | L2 | M1 | 12 | frozen, rapor | kanıt |
| E017 | B1 | L2 | M2 | 12 | frozen, rapor | kanıt |
| E018 | B1 | L2 | M3 | 12 | frozen, rapor | kanıt |
| E019 | B2 | L0 | M1 | 12 | frozen, rapor | kanıt (H1b) |
| E020 | B2 | L0 | M2 | 12 | frozen, rapor | kanıt (H1b) |
| E021 | B2 | L0 | M3 | 12 | frozen, rapor | kanıt (H1b) |
| E022 | B2 | L1 | M1 | 12 | frozen, rapor | kanıt |
| E023 | B2 | L1 | M2 | 12 | frozen, rapor | kanıt |
| E024 | B2 | L1 | M3 | 12 | frozen, rapor | kanıt |
| E025 | B2 | L2 | M1 | 12 | frozen, rapor | kanıt |
| E026 | B2 | L2 | M2 | 12 | frozen, rapor | kanıt |
| E027 | B2 | L2 | M3 | 12 | frozen, rapor | kanıt |
| E028 | B3 | L0 | M1 | 12 | frozen, rapor | kanıt |
| E029 | B3 | L0 | M2 | 12 | frozen, rapor | kanıt |
| E030 | B3 | L0 | M3 | 12 | frozen, rapor | kanıt |
| E031 | B3 | L1 | M1 | 12 | frozen, rapor | kanıt |
| E032 | B3 | L1 | M2 | 12 | frozen, rapor | kanıt |
| E033 | B3 | L1 | M3 | 12 | frozen, rapor | kanıt |
| E034 | B3 | L2 | M1 | 12 | frozen, rapor | kanıt |
| E035 | B3 | L2 | M2 | 12 | frozen, rapor | kanıt |
| E036 | B3 | L2 | M3 | 12 | frozen, rapor | kanıt |

- **Baseline cells (3):** `BASE×{L0,L1,L2}` — bench, hipotez sayılmaz.
- **İkincil TF blok (keşifsel, H2):** 15m→3h, h=12 (=3s) + diag {24(6s), 96(24s)},
  cost C aynı. S001..S008 = {B1,B3}×{L0,L1}×{M1,M3} (2×2×2), kendi FDR ailesi.
- `1h→6h` ve ek bloklar: bu turda YOK (sınırsız kombinasyon yasağı).
- Horizons (birincil matriste): **h=12 birincil kanıt**; ölçüm-diyagnostik
  (FDR dışı, keşifsel) kolonlar `h∈{3,36,72}` ve yalnızca final aday için
  `h∈{240,720}` (20s/60s). Ufuk ekseni matrisi BÜYÜTMEZ, rapor sütunudur.

**TOPLAM HİPOTEZ/CELL SAYISI (belirsizliği ortadan kaldırmak için):**
- Formal cell-level test: **36 (birincil, h=12) + 8 (ikincil TF) = 44**.
  Bunlardan yalnızca **birincil 36** Phase-5 PASS/FAIL belirler (bölüm 12).
- FDR aileleri: her label kolu ayrı (3 aile × 12 cell) + ikincil aile (8) = 4 aile.
- Baseline: 3 cell (bench). Seçim-sonrası kanıt (hipotez değil, gate): testleri
  aday üzerinde 3 seed sign-consistency, WF 8 fold (section 13), rejim/decile/horizon
  tabloları. Toplam hesaplı fit sayısı bölüm 19'da.

## 11. STATISTICAL TESTS (her birincil cell, validation OOF)

- Sınıflandırma (L0/L1): AUC, PR-AUC, logloss, Brier, ECE (10-bin calibration),
  directional accuracy, rank-IC (Spearman), + **decile/bucket tablosu**:
  her tahmin dilimi için mean/median future return, P(Y>0), P(Y>C), net(=mean−C),
  edge/cost. Doğrusal süreklilik kanıtı: decile indeksi × mean return **Kendall tau**.
- Regresyon (L2): R², RMSE, rank-IC, aynı bucketing predicted-değere göre.
- **Birincil sinyal istatistiği (PSS):** top-decile `mean future return − C`
  (normalize: `edge/cost = (mean10 − C)/C`). Konvansiyon anındaki asıl karar
  istatistiği budur. İkincil destek: rank-IC, AUC (L0/L1), Kendall tau.
- Karar istatistiklerinin seçim/hesaplama kodu rapordan BAĞIMSIZ frozen script'tir.

## 12. MULTIPLE COMPARISON CORRECTION

- BH-FDR, α=0.05 (`config/experiment.yaml multiple_comparison_correction`, kilitli).
- Aileler: label kol başına 12 cell (birincil), ikincil TF 8 — ayrı ayrı.
- **Aile yapısı kararı (M.20 karar taslağı — 2026-09-07, user): 4 aile KORUNUR
  + arm-marj notu.** Kayıt: 3 bağımsız label kolu birlikte kontrolde
  P(≥1 yanlış-pozitif kol) ≈ %14 civarı → PASS kolunun arm-gate'i (bölüm 22)
  marjla geçme şartı (PSS/edge, n-taban, CI-alt-uç) rapora belgelenir; aileler
  etkileşimli olduğu için efektif çok daha küçüktür. Rapora "nominal 44, efektif
  << 44" notu yazılır.
- **Selection leakage yok:** matris donduruldu; "en iyi kombinasyonu bul" DİYE
  tekrar yok; FDR sonrası kalan hücrelerden aday, bölüm 22 kurallarıyla (tek, frozen).
- Not (M.20 review): `argmax(edge/cost)` winner's-curse yanlılığı taşır —
  validation rakamları optimizm uyarısıyla raporlanır; nihai iddia yalnızca
  FINAL (2025H1) penceresindendir.

## 13. WALK-FORWARD DESIGN

- **Kırılım:** `config/experiment.yaml walk_forward` (KİLİTLİ): train 365 / val 90 /
  step 90, expanding false — Phase 2 `generate_folds` aynı üreteci, aralık
  `2020-01-01 → 2023-06-30` → ~9 fold (hepsi FINAL öncesi). Foldlar overlap →
  bağımsız DEĞİL (Anayasa 8; overlap raporlanır).
- **Akış:** kronolojik TRAIN → sonraki 90 gün VALIDATION (OOF), `random shuffle` YOK.
- **Kayıt:** WF yalnızca ana-val matrisinde KURTULAN hücrelerin aynı (frozen)
  config'iyle koşar (seçim-sonrası kanıt; matris → frozen kural → aday → WF sırası
  ön-kayıtlı). Her fold'da adayın PSS'i hesaplanır.
- **Tutarlılık eşiği:** fold'ların ≥ **%60**'ında PSS ana-val sonucuyla AYNI YÖNDE
  ve cost-aware anlamlı (net>0). Eşik kaynağı: `thresholds.phase_03_freqai.min_wf_win_rate`
  = 0.60 — **PROTOCOL-İÇİ, M.20 gerektirmez**.

## 14. COST MODEL

| Kalem | Değer | Kaynak |
|---|---|---|
| fee (entry+exit) | 0.001 × 2 | `config/experiment.yaml costs.fee_*` (kilitli) |
| slippage | 0.0005 × 2 | `costs.slippage_bps=5` (kilitli) |
| **C (round-trip)** | **0.003 = %0.30** | yukarıdaki kilitli parametrelerden TÜRETİLMİŞ, bu belgede sabit |
| haber-spike multiplier (2×) | raporlanır | Madde 12 (backtest ≠ gerçek) — bu faz P&L değil sinyal ölçer, nedenle sadece tek taraflılık için not |

- Her bucket/cell için rapor: gross expected return, fee, slippage, **net expected
  return**, **edge/cost ratio**. `edge/cost < 1` → **NO ECONOMIC EDGE** (user kuralı).

## 15. ECONOMIC EDGE CRITERIA

Birincil ekonomik gate: **PSS > 0 VE edge/cost ≥ 1.2** (sonraki getirinin maliyet
üzerinde %20 teminatı). Gerekçe: Phase 4.18 ~0.30% round-trip gerçekleşmesi ve
1h drift ≈ +0.015% ortamında, brüt premium'un maliyeti en az %20 aşması gerekir
(icra varyansı/gap payı). Bu eşik kilitli protokolde YOK →
**REQUIRES M.20 PROTOCOL APPROVAL** (ön-kayıt; ben LOCK ETMIYORUM).

## 16. REGIME ROBUSTNESS

- Kilitli mekanik sınıflandırıcı (`src/regime/classifier.py`: SMA50/200, ADX>20,
  ATR 30d percentile >0.70) — hindsight yok (Anayasa 9). Rapor grupları:
  bull, bear, sideways, sideways_high_vol (4.14 konvansiyonu).
- Yalnızca FİNAL aday için sunulur: rejim × decile (high/low-confidence) net/PSS.
- Tek rejimde sinyal varsa AÇIKÇA işaretlenir ve sinyal "rejim-şartlı" sayılır
  (faz başarısı iddiası sınırlanır). Rejim alt-grupları bağımsız örnek DEĞİLDİR.

## 17. FAILURE CRITERIA

Phase 5 FAIL/STOP (en az biri): (a) hiçbir label kolunda PSS kanıtı yok
(bölüm 12 kriterlerin hiçbiri TAM geçmiyor); (b) istatistiksel sinyal var ama
ekonomik edge yok (`edge/cost < 1` veya PSS ≤ 0); (c) FDR sonrası hücreler tek
blok + tek model kombinasyonuyla sınırlı (bölüm 12.7 anti-bağımlılık kuralı);
(d) WF tutarlılık <%60; (e) seed sign-consistency <2/3. FAIL durumunda
"biraz daha feature" sonsuzluğu AÇILMAZ (user §16); hattın kapatılması önerilir.

## 18. FINAL TEST PROTECTION (Phase 5 holdout)

- FINAL penceresine (**2025H1, bölüm 5'te karara bağlandı**): **tuning yok ·
  feature seçimi yok · model seçimi yok · threshold seçimi yok**. Yalnızca
  bölüm 22'deki frozen nihai aday TEK KEZ değerlendirilir ve SADECE raporlanır.
- Guard: `phase500_*` script'lerinde FINAL aralığına bakan hiçbir yükleyici/agregat
  yok; loader guard ABORT parametreli (bölüm 8). 2023H2'nin FreqAI finali olarak
  geçmiş tüketimi ve B/C'nin korunması bölüm 5'te belgelidir.

## 19. COMPUTE BUDGET

- Cap: **toplam ≤ 12 CPU-saat** (kilitli `rl_budget.max_train_hours=12` emsaliyle
  gerekçeli; PROTOCOL mantığı). Tahmini tipik: feature build (birincil+15m) ~5 dk;
  36 birincil cell (RF ~1-3 dk/cell, LGBM ~0.5-1 dk, LR ~sn) ~1 saat; aday
  seed/WF (bölüm 13, ≤12 aday × 8 fold × 1 seed) ~1-3 saat → **~4-6 saat**.
- Determinizm: her (cell, seed) için sabit RNG (numpy seed = hash(cell_id, seed));
  fitler deterministik ayarlı; çıktı hash manifest'i (examining Phase 3/4
  aggregate convention'ı). Seeds: çekirdek istatistik **seed=42**, dayanıklılık
  **{7,123}** (2/3 yön kuralı; Phase 3/4 seed convention'ı).
- GPU yok; TRAIN+VALIDATION için indirme YOK (mevcut feather + 15m resample).
  Yalnızca FINAL (2025H1) penceresi uygulamada indirilir (bölüm 5); tek değerlendirme
  bu hesaplamaların bütçesi dışındadır.

## 20. PROTOCOL IMPACT

- **Değişiklik YOK; hiçbir kilitli tanım/eşik değiştirilmedi.**
- Yeni dosyalar yalnızca: `scripts/phase500_*.py`, `tests/test_phase500.py`,
  `experiments/phase_05_ml/` (artefaktlar + bu belge).
- **M.20 KARAR TASLAĞI — 2026-09-07 (user):**
  1. Holdout = **2025H1 yeni pencere** (Final B ve C korunur; 2025H1 indirme
     uygulamada, indirme-sonrası-lock guard'ı ile).
  2. Eşik paketi (aşağıdaki 2–6 maddeler) **olduğu gibi M.20'e**; protokol-içi
     olanlar (FDR·d·power·WF·cost) kilitli kalır.
  3. Multiplisite: **4 aile korunur** + arm-marj notu (Bölüm 12).
  Bu kararlar LOCK DEĞİLDİR; resmî M.20 onayı kullanıcıya aittir (NO PROTOCOL LOCK).
- **REQUIRES M.20 PROTOCOL APPROVAL** maddeleri (yukarıda gerekçelendirildi):
  1. Bölüm 5 — Phase 5 korumalı holdout = **yeni rezervasyon 2025H1**
     (split tablosu, FINAL_TEST_P5) + uygulama anında 2025H1 veri indirme onayı.
  2. Bölüm 12 — sinyal-aşaması ana istatistiği (PSS, decile-premium) locked
     `oos_sharpe_ratio` yerine bu aşamanın ana metriği olarak ön-kaydı.
  3. Bölüm 15 — `edge/cost ≥ 1.2`.
  4. Bölüm 12 — AUC ≥ 0.55 / rank-IC ≥ 0.01 / Kendall tau > 0 taban değerleri
     (aşağıdaki "minimum pratik eşik" gerekçesi).
  5. Bölüm 12 — seed sign-consistency (≥ 2/3 seed) — Sharpe-based locked
     `seed_stability` istatistiğine dayanmayan yeni aile.
  6. Model-set fallback (LGBM yerine XGBoost) yalnızca kurulum yoksa.
- Protokol-içi (değişiklik gerektirmez, kaynak: `config/experiment.yaml`):
  α=0.05 BH-FDR · WF başarı ≥0.60 · Cohen d ≥0.30 · power ≥0.80 · cost parametreleri.

### Minimum pratik eşiklerin gerekçesi (kafadan değil)
- **AUC ≥ 0.55:** kullanıcı-örnek alt sınırı; intraday BTC sinyal literatüründe
  yayınlanan aralık ≈ 0.53–0.58 → orta bant. Amaç hücum istatistiği değil,
  PSS/edge/cost ana kapıdır; AUC destek kanıtıdır.
- **rank-IC ≥ +0.01:** Gu-Kelly-Xiu (JF, 2020) "Empirical Asset Pricing via ML"
  aylık IC ≈ 0.01–0.05 tabanı; intraday kısaltılmış horizonlarda bu alt sınırdır.
- **Cohen d ≥ 0.30, power ≥ 0.80:** lock'lu config eşikleri (yukarıdaki kaynaklar);
  d, top-decile vs bottom-decile future-return farkı üzerinden.
- **edge/cost ≥ 1.2:** 4.18 gerçekleşmesi (friction ≈ 0.30%) + icra varyansı payı;
  bu fazın "anlamlı ama ekonomik anlamsız" filtrelemesi (user §11).

## 21. EXACT IMPLEMENTATION FILES (onay sonrası, kapsam kilitli)

| Dosya | İçerik |
|---|---|
| `scripts/phase500_features.py` | UNION katalog (28 feature) + bloklar B0/B1/B2/B3; nedensellik assert'leri; → `phase_05_ml/features500.parquet` |
| `scripts/phase500_resample.py` | 5m→15m tamamlanmış-bar resample (nedensel) → `features500_15m.parquet` |
| `scripts/phase500_labels.py` | L0/L1/L2 üretici (C=0.003); off-by-one guard (base mum forward'a giremez) → `labels500.parquet` |
| `scripts/phase500_splits.py` | TRAIN/VAL kesimi + FINAL-guard (bölüm 5/8) + WF fold tarihleri (generate_folds, KİLİTLİ config) |
| `scripts/phase500_matrix.py` | Frozen matris çalıştırıcı (36 cell + 3 baseline + ikincil 8); per (cell,seed) deterministik fit → `results/oof_predictions500.parquet`, `results/matrix500.json` |
| `scripts/phase500_metrics.py` | Hücre metrikleri: AUC/PR-AUC/logloss/Brier/ECE/DA/rank-IC/decile tablosu/net/edge_cost; FDR per aile; horizon curve → `results/metrics500.json` |
| `scripts/phase500_gate.py` | Bölüm 12/15/17 kurallarının deterministik uygulaması (frozen) + aday seçimi (bölüm 22) → `results/gate500.json` |
| `scripts/phase500_walkforward.py` | Aday üzerinde 9 fold WF tutarlılığı (≤12 aday) → `results/wf500.json` |
| `scripts/phase500_report.py` | `REPORT_500.md` üretir (22 bölüm şablonu); Regime tablosu final aday için |
| `tests/test_phase500.py` | Leakage (feature≤t), off-by-one (base mum), FINAL-guard, resample-bütünlük, determinizm, PSS hesabı, FDR-kodu — sentetik fixture'lar |
| Çıktı | `experiments/phase_05_ml/REPORT_500.md` + parquet/json artefaktları + hash manifest |

## 22. DECISION TREE (ön-kayıtlı)

1. **Koştur:** frozen matrix (seed 42 çekirdek) → metrics → FDR.
2. **Arm gate** (her label kolu için): (a) ≥1 FDR-geçerli cell (α=0.05)
   AYNI ANDA ≥2 farklı blok VE ≥2 farklı model tarafından temsil ediliyor;
   (b) o cell'lerde AUC≥0.55 VE rank-IC≥0.01 VE Kendall tau>0 (destek);
   (c) **PSS > 0 VE edge/cost ≥ 1.2**; (d) Cohen d ≥ 0.30, power ≥ 0.80.
3. **Aday seçimi** (frozen tek kural): arm gate'lerden geçen TÜM hücreler içinde
   `argmax(edge/cost)`, tie-break düşük cell ID. Bu aday alır:
   3-seed sign-consistency ({42,7,123} ≥2/3 yön) → WF tutarlılık (%≥60) →
   rejim/decile/horizon tabloları → (onaylanırsa) FINAL penceresinde TEK DEĞERLENDİRME.
4. **Başarı (Phase 5 PASS):** ≥1 arm gate TAM geçti VE aday seed+WF ettiler.
   Sonuç raporlanır; STRATEJİ/BACKTEST otomatik DEĞİL — ayrı tasarım + M.20 onayı.
5. **Başarısızlık (Phase 5 FAIL → STOP):** hiçbir arm gate tam geçmedi /
   ekonomik edge yok / WF<%60 / seed yön<2/3 / tek-kombinasyon bağımlılığı.
   Sonsuz feature araştırması açılmaz; LINEAR KAPATILIR.

---

## SONUÇ (bu turda)

NO CODE · NO TRAINING · NO TUNING · NO BACKTEST · NO FINAL TEST · NO DATA DOWNLOAD
· NO PROTOCOL LOCK CHANGE.

Tek çıktı bu belgedir. Kullanıcı onayı olmadan hiçbir script/test/fold değeri
yazılmayacak. M.20 karar taslağı 2026-09-07'de netleştirildi: holdout = 2025H1
(B/C korunur, indirme ayrı onay), eşik paketi olduğu gibi M.20'e, multiplisite
= 4 aile + arm-marj notu. Bu kararlar LOCK DEĞİL — resmî M.20 onayı + 2025H1
indirme onayı kullanıcıdadır.

**READY FOR USER DECISION — M.20 formalization + 2025H1 indirme onayı bekleniyor**
