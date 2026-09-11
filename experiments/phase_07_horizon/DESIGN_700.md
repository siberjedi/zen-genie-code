# DESIGN 700 — Phase 7 H48 Experiment (PREREGISTRATION, ONAY YOK)

**Statü:** TASARIM. Deney çalıştırılmadı, veri indirilmedi, fit yok, backtest
yok, holdout kapalı, M.20 değişikliği yok, commit yok.
**Amaç (tek cümle):** 5m kısa-vadeli sinyalin 4h swing horizonunda ekonomik
hale gelip gelmediğini test etmek. "En iyi horizon'u bulmak" DEĞİL.
**Referanslar:** PHASE_07_SCOUT.md, DESIGN_500, TRAIN_VALIDATION_RESULTS,
6A/6B/6C lock-run-reportları, DESIGN_418, PROTOCOL.md, config/experiment.yaml.

## 0. Kilitli seçimler (özet)

H=48 (4h) tek primary horizon; fallback YOK; H72 (keşifsel tepesi) SEÇİLMEDİ
ve fallback OLAMAZ (sonuç kötü çıkarsa H72'ye dönülmez; 12h/24h açılmaz).
Prediction = holding horizon (PSS çerçevesi gereği, §2).

## 0b. Evidential status — H48 selection-risk (kilitli yorum)

- H48, keşifsel ufuk-bilgisi (h=72 ipucu) görüldükten sonra seçildi. Dolayısıyla
  H48 **tam anlamıyla confirmatory bir primary test DEĞİLDİR**; horizon-selection
  information mevcuttur ve sonucu etkileyebilir (yön: PASS-lehine şişirme).
- Buna rağmen deney **tek-atışlı, yanlışlanabilir exploratory hypothesis test**
  olarak yürütülür: tüm makine kilitli, fallback yok, FAIL hattı kapatır.
  Asimetri kaydı: selection PASS olasılığını şişirir ama FAIL olasılığını
  şişirmez → FAIL tam güçlü kanıttır; PASS zayıf kanıttır.
- PROTOCOL uygulanabilirliği: operasyonel makine (metrik, gate'ler, WF, seed'ler)
  aynen uygulanır; **yorum DOWNGRADE kilitlidir: PASS = "clean confirmatory
  evidence" DEĞİLDİR; PASS = "exploratory hipotez ilk falsifikasyondan sağ çıktı
  → confirmatory-replikasyon adayı (ayrı M.20, örn. P5)".** Final edge iddiası
  için replikasyon şarttır. M.20 "clean-confirmatory-or-nothing" isterse bu
  tasarım STOP sayılır (karar otoritenindir; bu belge downgrade yolunu kilitler).

## 1. Exact label formula (L1@H48)

`Y(t) = close[t+48]/close[t] − 1` (base mumu forward'da YOK; off-by-one guard
Phase 5 ile aynı). `L1(t) = 1{Y(t) > C}`, C=0.003. Label-bound: `t ≤ VAL_END −
48 bar`; son VAL satırı 2023-06-29 23:55 (etiketler 2023-06-30 23:55'i aşmaz,
korumalı veri gerekmez). NaN politikası: doldurma yok, düşürme var (aynen).

## 2. Execution (preregistered)

- **Sinyal:** `s(t)` = M2 model skoru (TRAIN-fit, VAL'de OOS).
- **Eşik (frozen, causal):** `q90_TRAIN` = TRAIN skorlarının 90. persentili
  (pooled, fit sonrası bir kez hesaplanır, dondurulur). Entry iff
  `s_VAL(t) ≥ q90_TRAIN`. VAL-pooled-decile YOK (lookahead olurdu).
- **Entry price:** `close[t]`; **exit:** `close[t+48]`; overlapping hold'lar
  serbest; event getirisi `r_i = Y_i(48) − C` (maliyet girişte tam tahsil —
  muhafazakar-muhasebe, net event-getirisini değiştirmez).
- **Lookahead kontrolü:** eşik TRAIN-only; skorlar TRAIN-fit; etiket-bound §1;
  causality probe; event-tarih ≤ VAL_END−48 assert'i.

## 3. Cost model (kilitli)

C = 0.003 = fee 0.001×2 + slip 5bps×2, event başına bir round-trip.
Bileşen muhasebesi: rapor `mean(Y_i)` (gross) vs `C` (cost) ayrıştırması içerir
(gross-vs-cost impact, secondary). Sonuçtan sonra cost DEĞİŞMEZ.

## 4. BASE-7 (kilitli)

B3 (28 feature, mevcut tanımlar verbatim). 6A/6B/6C ek feature'ları YOK.
Yeni feature fishing YASAK (Madde 10/20 ihlali sayılır).

## 5. Data split (kilitli)

TRAIN 2020-01-01→2022-12-31; VAL 2023-01-01→2023-06-30 (aynı pencereler, yeni
etiketler). Phase 7 final testi = FINAL_P5 (2025H1) REZERVE (ayrı M.20 ile,
otomatik açılmaz). FINAL_A (tüketildi) yeniden kullanılmaz. B/C/A kapalı.

## 6. Sample loss (önceden muhasebe)

H48 bound ek ~36 VAL satırı kaybettirir (51.798 → ~51.762); feature warmup
değişmez (~311 TRAIN satırı). Post-hoc kayıp-eşiği YOK (sayı icat edilmez);
genel QC (dropna, no-fill) aynen. Sayılar raporda ölçülür, gate değildir
(güç gate'i §9'da ayrı).

## 7. Statistics (kilitli — tam formalizasyon)

**7a. Exact formula.** Event kümesi `S = {t ∈ VAL : s(t) ≥ q90_TRAIN}`,
`N = |S|`. Event getirisi `r_i = Y_i(48) − C`,
`Y_i(48) = close[t_i+48]/close[t_i] − 1` (sabit 48-bar tutuş; overlapping
hold'lar serbest; aynı anda birden çok pozisyon mümkün, cap YOK —
her event event-uzayında eşit ağırlıklı).
`μ = mean(r_i)`, `σ = sd(r_i)` (ddof=1).
Yıllıklandırma: `λ` = yıllık event hızı = `N × 365/181` (VAL 181 gün; λ
gözlenen SABİT, yeniden tahmin edilmez).
**Primary metric: `θ = (μ/σ) × √λ`.**

**7b. Sampling unit & annualization convention.** Örneklem birimi EVENT'tir
(trade); takvimde eşit-aralıklı DEĞİLDİR. Klasik günlük-bar Sharpe
annualization'ı (`√252`) BURADA GEÇERLİ DEĞİLDİR ve θ literatür günlük-Sharpe
eşikleriyle (örn. "Sharpe>1") KARŞILAŞTIRILAMAZ — tek geçerli karşılaştırma
null'a karşıdır (H0: θ ≤ 0) ve aynı-konstrüksiyon θ_12 betimleyicisinedir (§7d).
Annualization gerekçesi: zayıf-bağımlı eventlerde yıllık getiri ≈ λμ, yıllık
vol ≈ σ√λ → oran (μ/σ)√λ; bu bir ölçek-konvansiyonudur, bağımlılık varsayımı
değildir. Overlap pozitif otokorelasyon üretir → gerçek yıllık vol DAHA
büyüktür → √λ nokta-tahmini İYİMSERDİR; bu yüzden karar CI-alt-sınırıyla
verilir (muhafazakar yöne denge) ve bağımlılık çıkarımda ele alınır (§7c).

**7c. CI construction (kilitli block bootstrap).** Uygulama serisi: giriş
zamanına göre sıralı event serisi `(r_1…r_N)`. Yöntem: moving-block bootstrap,
blok = ARDIŞIK 500 EVENT (tipik takvim karşılığı ~3.300–10.000 bar ≫ 48-bar
overlap penceresi → bağımlılık yakalanır), non-circular, kuyruk düşer;
10.000 resample, seed 42; her resample'da `θ* = (μ*/σ*) × √λ_sabit`
(λ dondurulmuş ölçek sabiti). CI95 = persentil [2.5, 97.5].
**Uyumluluk kanıtı:** λ sabit çarpan olduğundan `CI(θ) = √λ × CI(per-trade
Sharpe)` — ölçekli istatistiğin resample dağılımı, dağılımın ölçeğidir;
persentil CI monoton dönüşüm altında korunur. // K=500 sabittir (koşullu-K
yok); N küçüklüğüne karşı koruma = power gate (§9d/§13).

**7d. Economic estimand & BASE karşılaştırması (aynı estimand doğrulaması).**
Primary estimand θ_48 (§7a). Karşılaştırıcı θ_12 = AYNI §2/§7 konstrüksiyonunun
H=12'ye uygulanması (E032-verbatim refit ile ölçülür — betimsel, FDR-muaf,
gate DEĞİL; refit deterministik, PSS'i kayıtlı E032 ile 1e-9 içinde tutmazsa
STOP). Aynı-estimand doğrulaması: θ_48 ve θ_12 AYNI formül + AYNI annualization
konvansiyonu + AYNI bootstrap-CI makinesiyle hesaplanır; tek fark H'dir.
Resmi Δ-testi YOK (gerekçe: horizonlar-arası eşleştirme portföy-motoru
karmaşası gerektirir; mutlak-geçerlilik gate'i — θ_48 CI-alt>0 + edge≥1.2 +
tam zincir — "ekonomik anlamlılık" sorusunu zaten cevaplar). Δθ raporlanır,
karar ÜRETMEZ.

**Secondary (kilitli liste):** Net Return (event toplamı), MaxDD (event-eşdeğer
eğri), Sortino, Profit Factor, Win Rate, turnover (events/year + eşzamanlı-hold
ortalaması), gross-vs-cost ayrışımı, PSS/edge (süreklilik).

## 8. Multiple comparisons (kilitli)

Tek primary hypothesis, tek test (tek kol, tek horizon). FDR familyası =
1 test (BH trivial). Başka horizon fit EDİLMEZ → multiplicity avantajı YOK.

## 9. Success gates (yalnızca mevcut sayılar)

(a) PSS>0 ∧ edge/cost≥1.2 [mevcut]; (b) destek AUC≥0.55 ∧ rank-IC≥0.01 ∧ tau>0
[mevcut]; (c) θ CI95-alt > 0 [null-testi; 6A/6B ΔCI emsali kategoride, yeni
eşik değil — büyüklük eşiği YOK, literatür-Sharpe karşılaştırması YOK];
(d) d≥0.30 ∧ power≥0.80 [mevcut]; (e) FDR q<0.05 [mevcut, trivial];
(f) MaxDD ≤ 0.20 [config phase_05_compare mevcut]; (g) WF ≥0.60
[mevcut, H48 pipeline'ında]; (h) seed ≥2/3 [mevcut]. θ_12 karşılaştırıcı
betimseldir (§7d), gate DEĞİLDİR. Yeni threshold YOK.
Phase-3 mantığından devralınanlar: Sharpe-ölçeği, WF, MaxDD, effect/power
(yukarıda eşleşti); uygulanamayan yok.

## 10. Walk-forward (kilitli)

Fold yapısı aynen (365/90/90/90, expanding=false, ~9 fold); metrik fold-PSS
işaret-tutarlılığı ≥0.60. Overlap → bağımsızlık iddiası YOK (yön-göstergesi,
Madde 8). Fold etiketleri H48-bound ile kesilir.

## 11. Turnover (kilitli rol)

YALNIZCA preregistered secondary diagnostic (events/year, overlap profili).
Optimize EDİLMEZ, gate DEĞİLDİR, sonuç sonrası kurala bağlanmaz.

## 12. Hypothesis (exact estimand)

`S = {t ∈ VAL : s(t) ≥ q90_TRAIN}`, `r_i = Y_i(48) − C`, `θ` §7'deki gibi.
**H0:** θ ≤ 0 (H48 sinyalinin maliyet-sonrası ekonomik incremental edge'i yok).
**H1:** θ > 0 VE §9 zinciri tam geçer. Ekonomik karşılaştırıcı θ_12 §7d'de
(aynı estimand-ailesi, betimsel).

## 13. STOP rules (kilitli)

Veri-integrity failure (grid gap/dup) · leakage (probe/bound ihlali) ·
holdout contamination · reproducibility failure (determinizm self-check,
tol 1e-9; θ_12 refit'inin PSS'i kayıtlı E032 ile 1e-9 içinde tutmazsa STOP) ·
yetersiz güç (power<0.80 → STOP, FAIL değil).

## 14. Anti-fishing (kilitli)

Başlangıçtan sonra: H, cost, feature, model, threshold değişmez; fallback
çalıştırılamaz; H48 FAIL → ufuk hattı KAPANIR.

## 15. Final decision tree

STOP-koşulu → **STOP** (sonuç üretilmez) · tüm gate'ler PASS → **PASS**
("H48 ECONOMIC EDGE — exploratory-survival; clean-confirmatory DEĞİL, ayrı
M.20 ile replikasyon adayı", §0b yorumu kilitlidir) · herhangi gate FAIL →
**FAIL** ("NO H48 EDGE"; 12h/24h retry YOK).

## Selection-risk notu (kilitli hüküm §0b'de)

H48, h=72 keşifsel ipucu bilinerek seçildi. Azaltıcılar: ipucu-tepesi (72)
seçilmedi; seçim mekanizma-gerekçeli (ücret-amortismanı + özellik-ölçek uyumu);
fallback yok; blok-itiraf bu belgede. Bunlara ek §0b yorumu bağlayıcıdır:
PASS exploratory-survival sayılır, confirmatory kanıt sayılmaz. Nihai yargı
M.20'nindir (clean-confirmatory-or-nothing isterse bu tasarım STOP sayılır).

## M.20 değişiklik listesi (HENÜZ UYGULANMADI — dosyalar değişmedi)

**config/experiment.yaml** (önerilen ekler):
```yaml
splits:
  phase_07_horizon:
    train: "2020-01-01 → 2022-12-31"
    validation: "2023-01-01 → 2023-06-30"
    label_H: 48
    threshold_q90_train: "<fit sonrası hesaplanacak, dondurulacak>"
phase_07:
  seed_core: 42
  cost_C: 0.003
  n_boot: 10000
  bootstrap: "event-indexed moving blocks, K=500 events, lambda frozen"
  theta12_comparator_refit: true  # E032-verbatim, betimsel, gate-dışı
  evidential_status: "exploratory-hypothesis-test (non-confirmatory, §0b)"
  cpu_cap_hours: 12
```
**PROTOCOL.md:** değişiklik GEREKMEZ (OOS Sharpe zaten candidate primary;
tek-test preregistrasyon Anayasa ile uyumlu; Anayasa 20 maddesine ek yok).

**READY FOR M.20 REVIEW**
