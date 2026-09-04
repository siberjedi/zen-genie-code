# Phase 3.5 Diagnosis — 2026-09-04 (salt-okunur teşhis, değişiklik YOK)

> Kapsam: validation seed 2026 (seçilmiş) + dondurulmuş model (inference-only) +
> mevcut CSV/zip/feather. Eğitim YOK, Final Test A YOK (okuma bile yok),
> backtest YOK, düzeltme YOK. Phase 3 sonucu aynen duruyor.

## A. Executive summary
FreqAI'ın ~16k trade'i bir bug'dan değil, üç katmanlı bir tasarım etkileşiminden
doğuyor: (1) proba dağılımının %44'ü gri bölgede + tek 0.5 eşiği → sinyal flip'i;
(2) label 1-saatlik hareket hedeflerken efektif hold medyan 5dk → hedef-hold
uyumsuzluğu; (3) threshold == fee (sıfır marj) → yakalanan her hareket zaten
maliyet sınırında. Kritik ayrım: **fee öncesi gross +47.1 POZİTİF** (fee 147.2 →
net -100.0). Modelde zayıf ama gerçek bir ayrıştırma var (AUC 0.61, monoton
kalibrasyon); turnover bunu fee'ye gömüyor. Hüküm: **B+C hibriti (A reddedildi)**,
implementation temiz.

## B. Signal churn (`diagnosis/churn_by_pair.csv`)
- Toplam flip: 66,690 (18 pair, pair başına ~3,705; ~20 flip/gün/pair).
- Run-length: medyan 2 mum, ortalama 12.2 (uzun kuyruk), P25=1, P75=7, P90=26, P95=52.
- Aynı-sinyalde kalma: 5dk %91.8, 15dk %88.8, 30dk %85.8, 60dk %81.4.
  Oranlar masum görünür ama mum başına %8.2 flip × 815k sinyal = 66k flip.
- Gereksiz flip (izole tek mum `010`/`101`): 26,699 = tüm sinyallerin %3.3'ü.
- Baseline karşılaştırma: aynı pencerede 714 trade (4.0/gün) vs FreqAI 15,603
  (86.7/gün) — ~22x turnover farkı.

## C. Prediction distribution (`diagnosis/proba_hist.csv`, `calibration.csv`)
- proba: ortalama 0.457, std 0.068, aralık [0.218, 0.933] — yayılım VAR (saf coin-flip değil).
- Gri bölge [0.45–0.55]: sinyallerin **%44.0'ı** — tek 0.5 eşiği gürültünün tam
  ortasından kesiyor; flip'lerin ana kaynağı.
- AUC (kilitli label'a karşı): **0.6084** — zayıf ama gerçek ayrıştırma.
- Kalibrasyon monoton: bin ortalaması arttıkça label oranı 0.14 → 1.0 yükseliyor
  (seviyeler kayık: örn. p≈0.53 → oran 0.42). Sıralama bilgisi var, eşik bilgisi zayıf.

## D. Label economics (`diagnosis/label_economics.csv`, threshold DEĞİŞMEDİ)
- Validation label oranı: 0.328 (train 0.388 — dönem kayması not edildi, seçimde kullanılmadı).
- 12-mum ileri getiri: ortalama %0.004, std %0.849; P50 ≈ %0.000.
- P(fwd>thr)=0.328, P(fwd>2×thr)=0.205, P(fwd>4×thr)=0.087.
- E[fwd|label=1] = %0.715 → fee sonrası **%0.515**. Yani label "mükemmel"
  yakalansaydı bile işlem başına brüt marj ~%0.5; threshold == fee olduğu için
  tasarım marjı SIFIR (eşik == round-trip maliyet 0.002). Marj bırakılmamış.

## E. Fee/turnover breakdown (`diagnosis/cost_compare.csv`)
| taraf | n | gross+ | gross- | fee | net | işlem-başı gross | işlem-başı fee |
|-------|---|--------|--------|-----|-----|------------------|----------------|
| FreqAI | 15603 | +171.9 | -124.8 | 147.2 | -100.0 | +0.0030 | 0.0094 (3.1x) |
| Baseline | 714 | +174.5 | -168.7 | 45.2 | -39.4 | +0.0082 | 0.0633 (7.7x) |

- FreqAI fee ÖNCESİ pozitif (+47.1). Öldüren turnover×fee, modelin tamamı değil.
- Baseline'ın işlem-başı gross edge'i 2.7x büyük (0.0082 vs 0.0030) ve 22x az işlem yapıyor.
- Fee muhasebesi doğrulandı: örnek trade'te fee tek-kez/ayak, net == profit_abs (Phase 2 sanity).

## F. Holding period (`diagnosis/holding_buckets.csv`)
- Doğrulandı: medyan 5dk, ortalama 32dk, P25=5, P75=20, P90=70, P95=130.
- Hold-net korelasyonu: -0.149 (uzun tutuş daha kötü).
- Bucket'lar (n, gross, net, WR): ≤5m (8062, +56.36, -16.14, 0.34);
  5-15m (3120, +28.64, -2.64, 0.36); 15-60m (2709, +25.89, -1.60, 0.39);
  >60m (1712, -63.70, -79.59, 0.18).
- Kısa hold'lar brüt pozitif ama fee'ye yeniliyor; uzun hold'lar (takılmış
  kaybedenler) zararın büyük kısmı (-79.6 net). Label 1-saat hedeflerken
  trade'lerin %72'si ≤15dk kapanıyor: hedef-hold uyumsuzluğu.

## G. Model vs execution diagnosis
- **A) edge yok — REDDEDİLDİ.** Kanıt: AUC 0.608 (>0.5), monoton kalibrasyon,
  fee-öncesi gross +47.1. Saf coin-flip bu üçünü birden üretemez.
- **B) edge var ama turnover/fee yok ediyor — GÜÇLÜ.** Kanıt: +47.1 gross →
  147.2 fee → -100 net; işlem-başı fee/gross 3.1x; churn sayıları.
- **C) execution churn üretiyor — GÜÇLÜ (B ile birlikte).** Kanıt: medyan hold
  5dk vs label horizon 60dk; %44 gri bölge + tek eşik; izole flip %3.3;
  aynı-mum exit+re-entry quirk'i (aşağıda).
- **Hüküm: B+C hibriti.** Zayıf sinyal + onu fee'ye gömen execution.

## H. Baseline comparison
- Validation: baseline Sharpe -2.179 (714 trade) vs FreqAI -24.186 (15,603).
  Fark "model kötü" ile açıklanamaz TEK BAŞINA: farkın büyük kısmı turnover
  rejimi farkı (4.0 vs 86.7/gün). Frekans-nötr bakış: işlem-başı gross edge
  baseline 2.7x üstün (0.0082 vs 0.0030) — model kalite farkı GERÇEK ama
  Sharpe farkını (-22) büyüten çarpan turnover'dır.
- Final A sayıları bu teşhiste KULLANILMADI.

## I. Implementation sanity (statik + trace; DÜZELTME YOK)
Kod: `scripts/phase03_experiment.py:100-156` (`simulate`), trace:
`diagnosis/trace_checks.txt` — pair-içi overlap 0 pair, force_exit 1 (pencere
sonunda), duplicate (pair,open) 0, pencere-dışı trade 0.
- Hizalama: sinyal[t] (veri ≤t, testli) → icra close[t] (sıfır gecikme =
  iyimser varsayım, modeli FAVORE eder; yine de sonuç negatif).
- Lookahead: YOK (rolling/ewm nedensel, leakage testleri PASS).
- Fee: ayak-başı tek kez (nümerik doğrulandı). SL>ROI>sinyal önceliği
  (muhafazakar). SL/ROI intra-mum low/high ile (freqtrade'e yakın).
- **Quirk (rapor, düzeltme YOK):** ROI/SL çıkışıyla aynı mumda sinyal hâlâ 1 ise
  aynı kapanıştan RE-ENTRY yapılır (ekstra fee). Etkisi küçük ama churn yönünde.
- Train/validation hizalaması: slice sınırları + guard testleri PASS.
- **Hüküm: implementation temiz; kayıp modele+tasarıma ait, bug'a değil.**

## J. En güçlü 3 bulgu
1. **Fee öncesi +47.1 vs fee 147.2** — sorun turnover, saf model çöpü değil (AUC 0.61 destekler).
2. **Hedef-hold uyumsuzluğu** — 60dk label, 5dk medyan hold; yakalanan P&L etiketlenen hareket değil.
3. **Sıfır-marj tasarım** — threshold == fee; %44 gri bölge + tek eşik = churn jeneratörü.

## K. Sonraki araştırma için önerilen hipotezler (HENÜZ TEST EDİLMEDİ)

- HYPOTHESIS H1 — Histerezis bandı (örn. gir p>0.6 / çık p<0.4) churn'ü ve fee'yi
  keser, net'i çevirir.
  - NEDEN: %44 sinyal gri bölgede; tek eşik gürültüyü trade'e çeviriyor (Bölüm C).
  - NASIL TEST EDİLİR: Dondurulmuş proba'lar + bantlı simülasyonla validation'da
    paper deney (yeni faz onayı + Final A'ya dokunmadan).

- HYPOTHESIS H2 — Minimum hold/cooldown (örn. sinyal flip'inde 3-mum bekleme)
  efektif hold'u label horizon'a yaklaştırır.
  - NEDEN: trade'lerin %72'si ≤15dk kapanıyor, label 60dk hedefliyor (Bölüm F).
  - NASIL TEST EDİLİR: aynı proba'lar + hold-kısıtlı simülasyon (yeni faz).

- HYPOTHESIS H3 — Net-of-fee label (threshold = fee + tampon, örn. 0.004),
  marjlı hedef tanımı edge'i seçilebilir kılar.
  - NEDEN: mevcut eşik == maliyet, E[fwd|label=1] net yalnızca %0.5 (Bölüm D).
  - NASIL TEST EDİLİR: **Protokol değişikliği gerekir** (label tanımı kilitli) →
    yeni Final Test + Anayasa Madde 4/20 prosedürü; bu fazda DEĞİL.

- HYPOTHESIS H4 — Rejim-conditional sinyal kalitesi (train 0.388 vs val 0.328
  label oranı kayması): model bazı rejimlerde çalışıyor olabilir.
  - NEDEN: sınıf oranı dönemsel kayıyor; Phase 2 rejim altyapısı mevcut.
  - NASIL TEST EDİLİR: validation proba'larının rejim-kırılımlı AUC/kalibrasyonu
    (mevcut çıktılar + rejim etiketi; yeni backtest yok).

- HYPOTHESIS H5 — Aynı-mum re-entry quirk'i + 3-slot global kapışma, ölçülen
  turnover'ı şişiriyor olabilir.
  - NEDEN: Bölüm I quirk; etkisi küçük tahmin ediliyor ama ölçülmedi.
  - NASIL TEST EDİLİR: simülasyon varyantı (yeni faz; mevcut sonuç geçerli kalır).

Phase 3.5 COMPLETE — NO MODEL/PROTOCOL CHANGES
