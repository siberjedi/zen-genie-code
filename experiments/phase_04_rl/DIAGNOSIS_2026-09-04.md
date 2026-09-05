# Phase 4.2 RL Learning Dynamics Diagnosis — 2026-09-04 (salt-okunur, değişiklik YOK)

> Kapsam: kayıtlı 20 run + `curves_*.json` + `env.py` v4.1.0 kodu + scripted trace
> (eğitimsiz stepping) + feather okuma. Eğitim YOK, Final Test B YOK
> (okuma bile yok), düzeltme YOK, hipotez testi YOK.

## A. Reward density
- Flat iken reward matematiksel olarak TAM 0: pozisyon yok → portfolio sabit →
  log(1)=0. C0/42 eğrisi: 51,794/51,794 sıfır. Bu bug DEĞİL, tanım gereği.
- Holding iken MTM HER adımda üretiliyor: C0/7 eğrisinde 51,681/51,794 (%99.8)
  nonzero, ortalama |r|=8.8e-4, maks 0.029; toplam exact telescoping
  (Σr == log(final/init) = 0.607677). Kod (`env.py` step) + ampirik mutabık.

## B. Observation correctness
- Reset: pos=0, equity_norm=1.0, market son satırı close[29] ile eşleşiyor
  (float32 yuvarlama ~1e-3, zararsız).
- BUY sonrası pos-sütun kuyruğu 1'e dönüyor, equity-sütunu her adımda
  güncelleniyor; history penceresi nedensel kayıyor (testteki "all-1 False"
  doğru history davranışıdır, bug değil).
- Ölçek notu: market ham fiyat (~16k-60k), equity_norm ~1.0, position 0/1 —
  üç farklı büyüklük mertebesi tek MLP'de (bulgu, K-H3'e bağlanır).

## C. Action semantics
- BUY flat→long, SELL long→flat, HOLD korur; geçersiz aksiyon no-op + sayaç
  (BUY-while-long ve SELL-while-flat trace'de doğrulandı).
- SELL reward == log(equity_oranı) 1e-12 hassasiyetle (muhasebe exact).

## D. PPO dynamics
- Kayıtlı metrik YOK: loss/entropy/KL/clip/explained-variance hiçbir run'da
  loglanmadı (verbose=0, Monitor/TensorBoard yok) → bulgu F-DYN-1.
- Bilinenler: ~293 update/koşu (600k/2048; C2 ~147), rollout == update sayısı
  (tek env), LR sabit (C0/C2/C3 3e-4, C1 1e-4), episode ≈314,881 train adımı.
- Sonuç: collapse mekanizması içeriden GÖZLEMLENEMEDİ; yalnızca çıktılardan
  çıkarsanıyor (bölüm E).

## E. Policy collapse
- 18/20 saf HOLD (51,794 HOLD, 0 trade): tüm reward'lar 0 → advantage ~0 →
  politika init'ten kıpırdamıyor (sabit-nokta).
- 2/20 (seed 7, C0+C3) saf BUY: ilk adımda BUY, sonra 51,794 HOLD; SELL
  aksiyonu HİÇ örneklenmedi → çıkışın değeri hiç öğrenilemedi.
- İki attractor de sabit (flip=0) ve init-bağımlı (seed 7 iki config'de aynı).

## F. Buy-and-hold artifact
- Öğrenilmiş exit DEĞİL: 0 SELL aksiyonu; çıkış `terminated_forced`
  (close=2023-06-29 veri sonu).
- +83.32 = 2023H1 BTC rallisi (+%84, 16.5k→30.4k) şansı; giriş episode'un ilk
  adımı (02:30, 2023-01-01) → init-bias + forced-exit bileşimi.
- Reward-yapısı bileşeni: rallide hold MTM ile ödüllendiriliyor (pekiştirir),
  ama giriş de init şansı. Ağırlık: init-artifact GÜÇLÜ, forced-exit KESİN,
  öğrenilmiş karar YOK.

## G. Episode design
- 314,881 adımlık episode × 600k step ≈ 1.9 episode/koşu; update başına
  2048 adım (episode'un %0.65'i). 315k ufukta GAE kredi-atama + efektif
  ~1-bit/episode sinyal (trade et/etme sonucu) → PPO için zayıf öğrenme rejimi.
- Chunking (örn. 30-gün episode) SADECE hipotez (K-H3); uygulanMADI.

## H. Data/regime coverage
- Tek pair (BTC), train 314,911 / val 51,825 satır, hizalı, örtüşmesiz.
- Train 36 ay: ort +%3.9/ay, 18 negatif (halving+2021 boğa+2022 ayı tam döngü).
- Val 6 ay: ort +%11.8/ay, 1 negatif ([+39.8,+0.1,+23.0,+2.7,-6.9,+12.0]) —
  GÜÇLÜ ralli; train/val REJİM UYUMSUZLUĞU (ayı-ağırlıklı eğitim, ralli testi).

## I. Critical contradictions
- "MTM her step" vs "HOLD'da reward 0": ÇÖZÜLDÜ — çelişki yok. MTM pozisyon
  VARLIĞINA bağlı; flat portföy sabittir. Raporlardaki "0 reward" flat
  koşuların, "tek büyük reward" ise trade-seviyesi muhasebenin ifadesiydi;
  env-seviyesinde C0/7'de 51,681 MTM adımı var.
- "Tek büyük reward" ifadesi YANILTICI bulundu: büyük olan realize toplam,
  adım-adım MTM toplamıdır (telescoping exact).

## J. Result validity
- "Edge yok" kanıtı DEĞİL. "Öğrenemedi" kanıtı GÜÇLÜ:
  (1) politikalar init-sabit (18 koşu tek BUY bile denemedi, 2 koşu tek SELL
  bile denemedi); (2) 1.9 episode + ~293 update, 315k ufukta yetersiz;
  (3) tek "başarı" öğrenilmiş karar içermiyor (ilk-adım bias + forced exit);
  (4) entropi/value logları olmadığı için alternatif açıklama test edilemiyor.
- Deney edge hakkında BİLGİSİZ (negatif değil): inatçı HOLD politikası,
  kayıp yaşamadığı için risk davranışı da tanımsız (Phase 4 raporundaki
  vacuous-MaxDD notu geçerli).

## K. En güçlü 3 bulgu
1. **Reward yoğunluğu çelişkisi çözüldü:** flat=0 (tanım), holding=%99.8 MTM —
   efektif öğrenme sinyali episode-başına ~1 bit; PPO bu rejimde init'e çöküyor.
2. **+83 şans + forced exit:** öğrenilmiş tek karar yok (0 SELL); başarı hikayesi
   init-bias × ralli × episode-sonu NaN'ı.
3. **Ölçek + ufuk + rejim üçlüsü:** ham-fiyat obs (60k) vs 1e-4 reward'lar,
   315k-adım episode'da 293 update, ayı-eğitim/ralli-test — öğrenme koşulları
   baştan zayıf; teşhis için gerekli loglar (entropy/loss) hiç yok.

## L. Önerilen hipotezler (HİÇBİRİ TEST EDİLMEDİ)

- HYPOTHESIS H1 — MTM-dilüsyon: holding-süresince damlayan MTM, sell sinyalini
  boğuyor olabilir.
  - EVIDENCE: C0/7'de 51k mikro-reward toplamı = tek realized toplamla aynı.
  - TEST METHOD: realized-only reward varyantı ile izole A/B (protokol kararı gerekir).

- HYPOTHESIS H2 — Obs ölçek uyumsuzluğu gradyanı aç bırakıyor.
  - EVIDENCE: 60k-mertebe fiyat vs 1e-4 reward; Bölüm B.
  - TEST METHOD: train-istatistikli standardizer'lı env varyantı, leakage testli
    dry-run (eğitimsiz stepping + dağılım kontrolü).

- HYPOTHESIS H3 — Episode chunking (30-gün) kredi-atamayı düzeltir.
  - EVIDENCE: 1.9 episode/koşu, update başına %0.65 episode kapsamı (Bölüm G).
  - TEST METHOD: chunked env varyantında kısa smoke-eğitim (onaylı mini-bütçe ile).

- HYPOTHESIS H4 — Entropy çöküşü ölçülemediği için bilinmiyor.
  - EVIDENCE: log yok (F-DYN-1); sabit politikalar düşük-entropi ile uyumlu.
  - TEST METHOD: Monitor/TensorBoard loglu mini-koşu + entropy eğrisi (eğitim değil
    log-altyapı testi sayılır; yine de onaylı yapılmalı).

- HYPOTHESIS H5 — Rejim uyumsuzluğu sonucu şişiriyor (her iki yönde).
  - EVIDENCE: train %50 negatif ay vs val 1/6 negatif (Bölüm H).
  - TEST METHOD: ayı-penceresi validation ile simetrik değerlendirme (mevcut
    veri, Final B yok).

- HYPOTHESIS H6 — Sell-keşfi hiç örneklenmedi.
  - EVIDENCE: 20 koşuda toplam SELL aksiyonu ≈ 0 (18×0 + 2×0).
  - TEST METHOD: epsilon-greedy warmup'lı izole çalışma (protokol kararı gerekir).

Phase 4.2 COMPLETE — DIAGNOSTIC ONLY — NO TRAINING / NO PROTOCOL CHANGES
