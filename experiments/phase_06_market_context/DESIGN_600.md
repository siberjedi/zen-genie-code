# DESIGN 600 — Phase 6 Market-Context Research Scout (NO-LOCK draft)

**Durum:** TASLAK — lock yok, threshold yok, model yok. M.20 onayı olmadan deney başlamaz.
**Tarih:** 2026-09-08 · **Kapsam:** research scout + data feasibility + leakage audit + experiment design.
**Yasaklar:** training, tuning, backtest, model fit, feature selection, final test,
2025H1 / 2024H1 / 2024H2 / Final-A load veya download. Hepsi bu çalışmada YOK.

## 1. Research question

OHLCV-only feature setinin dışında, BTC/USDT 5m–1h trading kararlarına
**incremental information** taşıyabilecek yeni piyasa bilgi kaynakları var mı ve
bunlar **geçerli şekilde test edilebilir** mi?

## 2. Why Phase 5 stopped

- 44 formal cell (E001–E036 + 3 baseline + S001–S008), BH-FDR 4 aile: **0 q<0.05**.
- En iyi hücre E014 (B1/L1/M2): AUC 0.679, dir-acc ~0.77, rank-IC 0.043 —
  **ama PSS −0.00207, edge/cost −0.69 < 0**. Sinyal izi var, ekonomik edge yok.
- Phase 4.18: decision-level predictive edge YOK; RL ≈ exposure × drift.
- Karar: **daha fazla model deneme, yeni bilgi kaynağı ara.**

## 3. What counts as incremental information

Bir kaynak INCREMENTAL sayılır iff:
1. Mevcut 28 OHLCV feature'ından (B0–B3) türetilemez ( Granger-benzeri katma değer
   gelecek deneyde BASE vs BASE+SOURCE ile ölçülür),
2. Karar anında gerçekten biliniyordu (availability-time ≤ decision-time),
3. Locked cost C=0.003 altında ekonomik anlam taşıyabilecek horizon'da yaşar.

"New source model AUC 0.60" tek başına YETERLİ DEĞİL. Sorulacak:
ΔAUC? ΔrankIC? ΔPSS? Δedge/cost? (BASE'e karşı, §16 ablation.)

## 4. Candidate sources

| ID | Kaynak | Bağımsız aday |
|----|--------|----------------|
| A | Cross-asset / market context (majör coin returnleri, breadth, dominance, dispersion, correlation regime) | evet |
| B | Funding rate (BTCUSDT perp, 8h settlement) | evet |
| C | Open interest (değişim, z-score, price/OI divergence) | evet |
| D | Liquidations (long/short imbalance, burst, liq/volume) | evet |
| E | Order book / microstructure (imbalance, spread, depth) | evet |
| F | News / sentiment (timestamped, crypto-specific) | evet |
| G | X / social | SADECE feasibility — Phase 6'ya veri eklenmez |

Kaynaklar BİRLEŞTİRİLMEZ; her biri bağımsız candidate.

## 5. Data availability (özet; detay DATA_FEASIBILITY.md)

| ID | Ücretsiz resmi arşiv | Kapsama 2020→2023H1 |
|----|----------------------|---------------------|
| A | EVET — data.binance.vision klines (spot+futures, 5m, monthly zip, checksum) | TAM |
| B | EVET — `GET /fapi/v1/fundingRate` (1000/page, listing'den beri; BTCUSDT perp ~Eyl 2019) | TAM |
| C | KISMEN — resmi REST sadece son 30 gün; Vision daily metrics (günlük); intraday arşiv ücretli üçüncü parti | GÜNLÜK tam / intraday YOK (ücretsiz) |
| D | HAYIR — resmi arşiv yok (yalnızca canlı WS forceOrder); CoinGlass API ücretli planlarda 1m–5m aralık | Üçüncü partiyle MÜMKÜN |
| E | HAYIR — resmi arşiv yok; Tardis.dev (BTCUSDT spot L2 2019-12-01+, ücretli, TB ölçeği) | Ücretliyle MÜMKÜN |
| F | HAYIR — CryptoPanic ücretsiz API kalktı (04/2026); Growth 1-ay history; Enterprise 1-yıl, cursor-pag, tarih-aralığı yok | 2020–2023 backfill PRATİKTE YOK |
| G | KISMEN — X pay-per-use ($0.005/read, 2–3M cap) + üçüncü parti (twitterapi.io $0.00015/tweet); akademik tier kapalı | MÜMKÜN ama HOLD |

## 6. Timestamp rules

Her external değer için dört zaman ayrılır: DATA TIME / PUBLICATION TIME /
AVAILABILITY TIME / DECISION TIME. Kural: `availability_time ≤ decision_time`
olmayan değer kullanılmaz. 5m candle close = decision time; candle'a yazılan
her external değer o close'tan önce yayınlanmış olmalıdır. Detay LEAKAGE_MATRIX.md.

## 7. Leakage rules

1. Settlement serileri (funding): yalnızca **settlement sonrası** candle'larda.
2. Türetilmiş oranlar (OI z-score, liq/volume): pencere yalnızca geçmişi görür.
3. Haber/sosyal: publication_time + indexing delay ≤ decision_time; future
   article contamination ve duplicate kontrolü zorunlu.
4. Üçüncü-parti agregalar: metodoloji değişimi ve revizyon riski belgelenir;
   revize edilen seri kullanılmaz.
5. Günlük-güncel snapshot'lar (Vision daily metrics): karar candle'ının gününe
   ait değer, gün kapanmadan kullanılmaz.

## 8. Coverage

Locked Train/Validation: 2020-01-01 → 2023-06-30 (Val: 2023-01-01 → 2023-06-30).
Her kaynak için bu pencerede KESİN coverage gerekir; 2025H1 ile telafi YASAK.
Yalnızca güncel veri varsa: "locked pencerelerle yetersiz örtüşme" yazılır.

## 9. Cost considerations

C = 0.003 locked (fee 0.001×2 + slip 5bps×2). Değişmez. Haber anı slippage
çarpanı (config: 2x) haber-kaynaklı stratejilerde ayrıca modellenmelidir —
ama bu fazda model yok, yalnızca not.

## 10. Candidate experiments (lock YOK — öneri)

- Phase 6A: OHLCV baseline + cross-asset context
- Phase 6B: OHLCV baseline + funding
- Phase 6C: OHLCV baseline + OI (önce daily, sonra intraday-ücretli opsiyonu)
- Phase 6D: OHLCV baseline + liquidations
- Phase 6E: OHLCV baseline + order-book top-of-book subset
- Phase 6F/G: ŞİMDİLİK YOK (feasibility engeli; arşiv erişimi sağlanırsa revisit)

## 11. Ablation design

Her deneyde üç kol: BASE (Phase 5 frozen baseline) / NEW SOURCE only /
FULL (BASE + NEW SOURCE). Rapor metriği Δ (FULL − BASE): ΔAUC, ΔrankIC, ΔPSS,
Δedge/cost. NEW-only kolu tanısal; seçim kriteri FULL−BASE farkıdır.

## 12. Baseline definition

BASE = Phase 5'in frozen setup'ı: aynı splitler, aynı C, aynı metrikler
(PSS/edge/cost/rank-IC/Kendall/Cohen-d/power), aynı tohum disiplini.
Phase 5'te reddedilen model/feature/label/horizon kombinasyonları yeniden açılmaz.

## 13. Statistical design

Phase 5 machinery yeniden kullanılır: per-cell PSS t-testi, BH-FDR aileleri,
arm-gate mantığı, 3-seed sign-consistency, walk-forward tutarlılık (≥0.60).
Aile sayısı artarsa FDR güç kaybı plana yazılır (daha az kol önerilir).

## 14. Multiple comparison strategy

Her yeni kaynak = yeni karşılaştırma yükü. Kural: önce TEK kaynak (6A),
sonra sonuç ne olursa olsun durup raporla; ikinci kaynağa ancak ayrı M.20
kararıyla geçilir. Kaynaklar arası "en iyi seçme" fishing sayılır.

## 15. Economic criteria

Seçim eşiği Phase 5 ile aynı: PSS>0, edge/cost≥1.2, destek metrikleri,
d≥0.30, power≥0.80, q<0.05, WF≥0.60. Yeni threshold YOK.

## 16. Selection rules

Argmax(edge/cost) + tie-break + gate zinciri Phase 5'ten devralınır.
Scout score'u (HIGH/MEDIUM/LOW/REJECT) **feasibility** skorudur, performans
tahmini değildir — "kesin çalışır" iddiası YOK (§23).

## 17. Holdout protection

FINAL_TEST_P5 (2025H1), Final B (2024H1), Final C (2024H2), Final A (2023H2):
bu fazda load/download/score/selection YOK. Veri indirme planları 2023-06-30
sonrasını KAPSAMAZ (NO 2025H1 DOWNLOAD).

## 18. Data acquisition plan

Özet; detay DATA_FEASIBILITY.md §14 formatında (provider, method, size, CPU/
storage, timestamp normalizasyonu, quality checks, legal, reproducibility).
İndirme BU fazda yapılmaz.

## 19. Compute estimate

- 6A (cross-asset klines): indirme ~GB mertebesi, feature build Phase 5 ile aynı
  mertebe; toplam < 2 CPU-saat ek yük.
- 6B (funding): ~4k satır/sembol; ihmal edilebilir compute.
- 6C-günlük: ihmal edilebilir. 6C-intraday / 6D / 6E: veri hacmine bağlı
  (6E tam L2 = TB'lar → SADECE book_ticker/top-N subset ile feasible).

## 20. Decision gates

- GATE-1 (bu rapor): viable source var mı? → Karar A–E (§25).
- GATE-2 (M.20): hangi TEK deney lock'lansın?
- GATE-3 (deney sonrası): Phase 5 kriterleriyle FINAL TEST P5'e aday var mı?
