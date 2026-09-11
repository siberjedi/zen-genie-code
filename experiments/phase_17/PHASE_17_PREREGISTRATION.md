# PHASE 17 — PREREGISTRATION: LONG-ONLY TREND + VOL-TARGET

**Statü:** PROTOCOL. Backtest/parameter-search/fit/holdout YOK. Bu dosya sonuç
görülmeden önce kilitlendi (2026-09-10). Grid/parametreler bu dosyadan sonra
DEĞİŞTİRİLEMEZ.

---

## 1. HYPOTHESIS

- **H0:** Uzun ufuklu (4H/1D) low-turnover long-only trend exposure, BTC
  buy-and-hold'a karşı maliyet sonrası (C=0.003) anlamlı risk-ayarlı üstünlük
  sağlamaz.
- **H1:** 4H/1D trend-following + volatility targeting, long/short veya per-bar
  alpha tahmini YAPMADAN, crash-avoidance / exposure-timing mekanizmasıyla
  C=0.003 altında pozitif ve out-of-sample risk-ayarlı performans sağlar.

Test edilen hipotez **tek** bir estimand ailesidir: LOW-TURNOVER LONG-ONLY
EXPOSURE TIMING. Per-bar sinyal tahmini (P3/P5/P7/M.20 ailesi) DEĞİLDİR.

## 2. ESTIMAND (kilitli tanımlar)

- **Bar:** 4H veya 1D (agregasyon §8).
- **w_t:** bar t kapanışında belirlenen pozisyon ağırlığı = `signal_t × exposure_t`,
  `w_t ∈ [0, 1]`. w_t, r_{t+1} üzerinde kazanılır (decision at close of t,
  execution at open of t+1; `position = signal.shift(1)` konvansiyonu).
- **strategy return:** `r_strat_{t+1} = w_t × r_{t+1} − (C/2) × |w_{t+1} − w_t|`
- **benchmark return:** BTC buy-and-hold (w=1 sabit; başlangıç giriş maliyeti
  hariç — rapor BH-brüt olarak verilir, strateji ile aynı barlarda).
- **excess return:** `r_strat − r_BH` (bar-hizalı).
- **Sharpe:** yıllıklaştırılmış (bar başına mean/std × sqrt(bar_yıl)); n ≥ 180 bar
  (4H) / ≥ 120 bar (1D) koşuluyla hesaplanır, yoksa "yetersiz n".
- **Sortino:** Sharpe'ın downside-deviation versiyonu (hedef 0).
- **MaxDD:** w>0 dönemleri dahil tam equity serisi üzerinde.
- **CAGR / total return:** net equity serisinden.
- **turnover:** `Σ|w_t − w_{t-1}|` (tek yön); entry/exit/rebalance ayrı raporlanır (§5).
- **transaction cost:** C=0.003 round-trip kilitli (§6).
- **exposure:** zaman ortalaması `mean(w_t)`; `max(w_t) = 1.0` (kaldıraç YOK).
- **volatility target:** §4.

**P7 ayrımı (kayıt):** P7 H48, skor-eşikli EVENT-based long/short idi (647 event,
%1.2 oran, kuyruk-artefaktı θ=+5.47 / θ12=−5.91, MaxDD 0.963, M.20-confirm
θ=−10.22 → FINAL_P5 tüketildi). Bu deneyin estimand'ı farklıdır: sürekli
LONG/FLAT price-trend exposure, parametre fit'siz, düşük turnover. P7/M.20
sonuçları bu hipotezi OTOMATİK falsifiye etmez (§15).

## 3. STRATEGY FAMILY + EXACT CANDIDATE GRID (kilitli)

Pozisyon yalnızca LONG (w>0) veya FLAT (w=0). Short YOK. Kaldıraç YOK
(max exposure 1.0). Trend bozulursa LONG→FLAT; yeniden oluşursa FLAT→LONG.

İki mekanizma, iki horizon. **EXACT GRID (6 aday, a priori sıralı):**

| # | Mekanizma | Tanım | Horizon | Parametreler |
|---|-----------|-------|---------|--------------|
| 1 | price-vs-SMA | LONG iff close > SMA(N) | 4H | N=200 (~33 gün) — PRİMARY |
| 2 | SMA cross | LONG iff SMA(fast) > SMA(slow) | 4H | (50, 200) |
| 3 | Donchian breakout | LONG iff close > HH(N); FLAT iff close < LL(N) | 4H | N=200 |
| 4 | price-vs-SMA | LONG iff close > SMA(N) | 1D | N=50 |
| 5 | price-vs-SMA | LONG iff close > SMA(N) | 1D | N=100 |
| 6 | Donchian breakout | LONG iff close > HH(N); FLAT iff close < LL(N) | 1D | N=100 |

- HH/LL: son N barlık yüksek yüksek / düşük düşük (giriş-çıkış ayrı sinyal).
- SMA: bar kapanış fiyatı üzerinden, yalnızca kapalı barlar (shift(1)).
- Grid genişletilemez. Sonuç görüldükten sonra parametre/horizon/mekanizma
  ekleme-çıkarma YASAK.
- **Aday #1 (4H price-vs-SMA200) = PRIMARY.** Gerisi confirmatory.
  Primary gate'leri geçemezse, kullanılacak aday = önceden sabitlenmiş sıradaki
  (liste sırasıyla) tüm bireysel gate'leri geçen İLK aday. Sharpe sıralamasıyla
  seçim YAPILMAZ (post-hoc seçim yasağı, §13).

## 4. VOLATILITY TARGETING (kilitli)

- **estimator:** realized vol = son `L` bar getirisinin örnek std'si
  (4H: L=84 bar = 14 gün; 1D: L=30 bar = 30 gün).
- **annualization:** 4H: `sqrt(6 × 365)`; 1D: `sqrt(365)`.
- **target_vol:** `τ = 0.40` (yıllık, kilitli).
- **exposure:** `e_t = min(1.0, τ / σ_hat_t)`; **min_exposure = 0.25**,
  **max_exposure = 1.0** (kaldıraç yok).
- **rebalance frequency:** her sinyal barında (4H veya 1D) güncelleme.
- Kilitli parametreler (τ, L, min/max, anüalizasyon, rebalance) backtest sonrası
  değiştirilemez.
- Vol-target yalnızca exposure'ı ölçekler; FLAT/LONG sinyalini DEĞİŞTİRMEZ.
  w_t = 0 ise e_t'nin değeri yoktur (FLAT kalır).

## 5. TURNOVER

- **turnover_t = |w_t − w_{t-1}|** (tek yön birimi).
- Raporlar ayrı: (a) entry trade'leri (0→w>0), (b) exit trade'leri (w>0→0),
  (c) rebalance (sinyal değişmeden w değişimi — vol-target kaynaklı).
- Yıllık turnover oranı = `Σ|Δw| / yıl`.
- Beklenen yapı: structural low-turnover (hedef: yıllık birkaç-on trade),
  per-bar trading DEĞİL. Turnover > 100/yıl çıkan aday otomatik şüphelidir.

## 6. COST

- **Kilitli ana varsayım: C = 0.003 round-trip (30bp)** — P8-A kararı.
- Yalnızca önceden tanımlı sensitivity: **C ∈ {0.001, 0.003, 0.005}**.
- Maliyet bar başına `(C/2) × |Δw_t|` (tek yön 15bp; round-trip 30bp).
- **Ana karar C=0.003 üzerinden verilir.** C=0.001'deki pozitif sonuç tek başına
  PASS değildir.

## 7. BENCHMARK

- **BTC buy-and-hold** (aynı barlarda, brüt). Ayrıca raporlanır:
  excess return, benchmark-relative MaxDD, crash-pencere performansı
  (örnek: 2021-05, 2022 bear, 2023-06 arasındaki düşüş bölgeleri).
- Strateji yalnız Sharpe değil, drawdown/crash-risk profiliyle de
  benchmark'a karşı değerlendirilir.

## 8. DATA + AGREGASYON

- Kaynak: `freqtrade/user_data/data/binance/BTC_USDT-5m.feather`,
  `load_dataset_slice()` (2020-01-01 → 2023-06-30 23:55, PIT-temiz, tz-aware UTC).
- 4H/1D barlar 5m'den DETERMINISTIC agregasyon (kod tek, aşağıdaki tanım):
  - open = ilk 5m open; high = max; low = min; close = son 5m close;
    volume = toplam.
  - **timestamp = bar kapanışı** (end-label): 4H barlar UTC [00:00,04:00) →
    04:00 etiketi; 1D → ertesi gün 00:00 etiketi. Örtüşme yok.
- Sinyal yalnızca kapalı barlardan; pozisyon bir sonraki bara uygulanır
  (`shift(1)`). Gelecek bilgi sızıntısı YOK.
- Korunan pencereler (FINAL_A/B/C/P5) bu veri kümesinde zaten yok
  (`check_not_in_protected` guard'ı uygulanır).

## 9. WALK-FORWARD

- Pencere sabitleri (p5_splits, kilitli): TRAIN 2020-01-01→2022-12-31;
  VAL 2023-01-01→2023-06-30.
- Parametreler sabit olduğu için "fit" yok; WF = stabilite değerlendirmesi:
  - **7 overlap-sız fold:** 2020H1, 2020H2, 2021H1, 2021H2, 2022H1, 2022H2,
    2023H1(=VAL). Her fold için net performans C=0.003'te.
  - **Stabilite gate:** ≥5/7 fold net-pozitif (C=0.003).
- **Seçim dönemi = VAL (2023H1) yalnızca.** Tüm aday kararları VAL üzerinde;
  sonuçlar görüldükten sonra seçim dönemi değiştirilemez.
- Final holdout'a (FINAL_B/C) tuning/selection sırasında ERİŞİM YASAK
  (guard + registry, §10).

## 10. HOLDOUT

- **FINAL_A (2023H2) TÜKETİLDİ (P3). FINAL_P5 (2025H1) TÜKETİLDİ (M.20).**
  Kullanılabilir: **FINAL_B (2024H1)** veya **FINAL_C (2024H2)** — ikisi de
  UNTOUCHED. Planlanan: **FINAL_B birincil, FINAL_C yedek** (PHASE_17_HOLDOUT_PLAN.md).
- Protokol: (1) M.20 otoritesinden assignment kararı; (2) download-then-lock
  akışı (P5 emsali: feather + manifest + **sha256 pin** + registry kaydı);
  (3) `verify_holdout_hash` zorunlu; (4) tek değerlendirme; (5) tüketim kaydı.
- Holdout verisi bu fazda YOKTUR ve OKUNMAZ. Assignment öncesi hiçbir kod
  FINAL_B/C aralığına erişemez.

## 11. METRICS

- **PRIMARY: OOS (holdout) Sharpe** — C=0.003'te.
- SECONDARY: Net Return · MaxDD · Sortino · Profit Factor · Win Rate ·
  turnover (entry/exit/rebalance) · cost sensitivity (0.001/0.003/0.005) ·
  benchmark-relative (excess, drawdown profili, crash bölgeleri) ·
  vol-target açık/kapalı karşılaştırması (mekanizma ayrıştırması).

## 12. SUCCESS / FAILURE GATES

Mevcut proje hard gate'leri (yeni eşik icat EDİLMEZ; P8 kost-scout + P7 gate
seti referans):

- **G1:** OOS Sharpe ≥ 0.80 (C=0.003)
- **G2:** OOS MaxDD ≤ 0.20
- **G3:** WF stabilite: ≥5/7 fold net-pozitif
- **G4:** benchmark üstünlüğü: holdout'ta excess return > 0 VE MaxDD < BH MaxDD
- **G5:** edge tek dönem/tail event'e dayanmıyor (yıllık sub-pencere dağılımı)
- **G6:** parameter sensitivity: komşu grid parametreleri (N±20%) benzer sonuç
  (orijinal grid dışına çıkılmaz — yalnızca duyarlılık ölçümü)
- **G7:** cost sensitivity: C=0.005'te OOS Sharpe ≥ 0.40 (edge maliyette yok olmuyor)
- **G8:** vol-target leverage-artifact değil (max exposure 1.0; vol-target'sız
  versiyon da gate'leri ayrıca raporlanır)

**"positive Sharpe" tek başına PASS DEĞİLDİR** — yukarıdaki gate setinin
tamamı gerekir.

## 13. MULTIPLE COMPARISON

- Aile = 6 aday. **A priori PRIMARY = #1.** Kalan 5 confirmatory.
- Per-aday p-değeri: projenin mevcut block-bootstrap makinesi
  (phase505_stats, 10k bootstrap, seed 42) — Sharpe/θ CI.
- Aile üzerinde **Benjamini-Hochberg FDR** (mevcut `benjamini_hochberg`)
  uygulanır; q<0.10 eşiği kullanılır (mevcut proje konvansiyonu).
- Final aday seçimi: §3'teki SABİT öncelik sırası. "En yüksek Sharpe'ı
  seçtik" post-hoc seçimi YASAK. FDR'den geçmeyen confirmatory adaylar
  rapor edilir ama tez olarak sunulmaz.

## 14. FALSIFICATION

Aşağıdakilerden HERHANGİ biri → strateji FAIL (tüm grid ailesi adına):

1. C=0.003'te OOS performans negatif VEYA anlamsız (bootstrap CI sıfır içerir)
2. MaxDD gate (G2) başarısız
3. WF stabilitesi (G3) başarısız
4. Benchmark karşısında ekonomik üstünlük yok (G4)
5. Edge yalnızca tek dönem/tail event'e dayanıyor (G5)
6. Parametre duyarlılığı aşırı kırılgan (G6)
7. Vol-target sonucu leverage-artifact (G8)
8. Cost sensitivity'de edge yok oluyor (G7)

FAIL durumunda: yeni parametre/horizon arayışı YOK; hipotez ailesi kapanır.

## 15. P7 / M20 / P14 AYRIMI (kayıt)

- **P7 (H48 event-based signal): FAIL** — skor-eşikli event long/short.
- **M.20-confirm: NOT-CONFIRMED** — P7 sinyalinin bağımsız replikasyonu
  (θ=−10.22, AUC 0.5482); FINAL_P5 tüketildi.
- **P14 (aggTrades micro-flow): FAST DECAY** — 1s ufukta +0.005bp.
- Bunlar mevcut hipotezi OTOMATİK falsifiye ETMEZ: yeni estimand =
  **LOW-TURNOVER LONG-ONLY EXPOSURE TIMING** (trend-following, fit'siz,
  crash-avoidance). P2/P7'nin "momentum" başlığı altında test ettiği şey
  5m–4h per-bar sinyalleriydi; 4H/1D price-trend long/flat + vol-target
  ailesi bu projede HİÇ KOŞULMADI (Phase 16 audit, literature gap).

## 16. NO-PEEKING RULES

1. Grid/parametreler bu dosyayla kilitlendi; sonuç görülmeden önce son haliyle
   imzalıdır (faz kaydı).
2. VAL üzerinde bile aday verileri dışında keşifsel analiz YASAK.
3. FINAL_B/C'ye (veri yok) ve registry'ye dokunmak YASAK.
4. Kod, koşum öncesi review'dan geçer; sonuçlar freeze edilir.
5. Holdout assignment + hash pin + tüketim kaydı PHASE_17_HOLDOUT_PLAN.md.

---

VERDICT: PREREGISTRATION LOCKED — READY FOR PHASE 18 (implementation) upon
M.20 holdout-assignment approval.