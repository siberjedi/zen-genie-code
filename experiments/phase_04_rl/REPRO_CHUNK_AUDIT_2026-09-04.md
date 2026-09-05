# Phase 4.5 Reproducibility + Chunk Audit — 2026-09-04 (denetim-only)

> Eğitim YOK, tuning YOK, Final Test B YOK (okuma bile yok), düzeltme YOK,
> protokol/threshold/budget DEĞİŞİKLİĞİ YOK. Bulgular mevcut artifact + kod + salt-okunur sorgulardan.

## A. Reproducibility
- Smoke seed42 tekrarında val metrikleri identik (rounded), weight hash FARKLI.
  Yani: davranış-eşitliği gözlendi (tek örnek), bit-eşitliği YOK.
- `seed_all` kapsar: random/numpy/torch.manual_seed + cudnn flags.
  Kapsamaz: thread sayısı, deterministik-algoritma zorlaması, PYTHONHASHSEED.

## B. RNG analysis
- Donanım: CPU-only (`cuda_available: False`) → GPU nondeterminizmi ELENDİ.
- torch 8 thread + interop 8; OMP/MKL thread değişkenleri UNSET →
  oneDNN/MKL backward indirgemelerinde thread-scheduling dalgalanması
  (~1e-7 mertebe, update başına birikir). Birincil şüpheli.
- PYTHONHASHSEED UNSET → süreçler-arası set/dict sırası riski (kritik yollarda
  `sorted()` var, ama garanti yok).
- SB3 yolu deterministik: PPO(seed) → action_space/vec-env seed + seed'li
  minibatch shuffle; rollout sıralı; `use_deterministic_algorithms` AÇIK DEĞİL,
  CUBLAS değişkeni YOK (CPU'da ilgisiz).
- Sonuç: aynı-seed farklı-ağırlık BEKLENEN rejimde (single-thread kilidi yok).

## C. Weight hash discrepancy
- Hash'ler tüm parametre yaprakları üzerinden (sıralı, deterministik serileme) →
  fark GERÇEK ağırlık farkı, artefakt değil.
- Val metrik eşitliğiyle çelişmez: farklı ağırlıklar aynı argmax aksiyonları
  üretebilir (özellikle dejenere/yakın-dejenere politikalarda). Bu örnekte
  187 trade'in metrikleri 3-ondalıkta aynı çıktı; GARANTİ DEĞİL, gözlem.
- Seviyeler: (1) aynı metrik — gözlendi, garanti yok; (2) aynı ağırlık —
  YOK (kanıtlı farklı); (3) bit-identical training — YOK.

## D. Action sequence reproducibility
- DOĞRULANAMAZ durumda: val action sequence'leri ve equity eğrileri
  persist EDİLMEDİ (sadece sayımlar + metrikler var). Tekrar koşmak = training
  sayılır → bu fazda YASAK. Gereken fix: sequence/equity hash'lerinin
  kaydedilmesi (aşağıda J).

## E. Chunk semantics (kod-doğrulamalı)
- Sınırlar: `[0,5000) + [5000,10000) + …`, sıralı non-overlapping partition;
  kalıntı `>= window+1` ise tutulur, değilse atılır (test 1).
- Kronoloji korunur (iloc dilim, shuffle YOK) → train-içi leakage YOK.
- Validation chunk'lanmaz (tam-pencere `TradingEnv`) → train/val overlap YOK
  (tarih filtresi + guard'lar aktif).
- Chunk sonu: base forced-liquidation (fee+slippage'li, reward'a exact) +
  `terminated=True` (bootstrap gerekmez — getiri realize). Sessiz drop YOK (test 2).
- Reset: cash=initial, flat, history prefill — ÖNCEKİ chunk state'i TAŞINMAZ.
- Aynı dönem iki chunk'a kopyalanamaz (disjoint partition + mod-rotasyon;
  wrap-around tam tur sonrası, deterministik).
- İncelik: constructor ilk reset'i tüketir (ilk episode chunk 1'den başlar);
  63 chunk/120 episode'da chunk 0 bir kez görülür — deterministik, belgeli.

## F. Forced liquidation
- Formül fee/slippage dahil, MTM telescoping 1e-9 exact (test + probe).
- Chunk sınırı = ekonomik olarak gerçek bir kapanış; "bedava" unsur YOK.

## G. Max-hold implications (ANALİZ, değişiklik YOK)
- 5,000 mum ≈ 17.4 gün tavan hold; 17+ günlük strateji alanı kapalı.
- Sınır çıkışları turnover'a eklenir (kapanış + olası re-entry) — ekonomik
  exact olduğu için bedava öğle yemeği yok, ama hold-süresi dağılımı
  sola eğilir (Phase 4'ün 180-gün hold'u bu rejimde İMKANSIZ).
- Öğrenme etkisi: uzun-trend taşıma ödüllendirilemez → momentum-uzun
  politikalar yapısal dezavantajlı. Bilinçli trade-off (çeşitlilik karşılığı).

## H. Smoke variance
- n=2 seed, 20k step, ent 0.01: seed42 (187 trade/-6.6) vs seed7 (1814/-99.1)
  farkı exploration/init varyansıdır; KARŞILAŞTIRMA DEĞİLDIR (başarı/başarısızlık
  etiketi YOK). Phase-4 seed42 (0 trade) ile kıyaslanamaz (farklı env: normalized
  + chunked + ent) — kıyaslama tuzağına düşülmedi.

## I. Blockers
- **R1** Bit-determinizm yok (threading kanıtlı). **R2** Action-sequence/equity-curve
  hash'leri persist edilmiyor → tekrar-üretilebilirlik DOĞRULANAMAZ. **R3** Model
  dosyaları smoke'ta kaydedilmedi (hash yalnızca raporda).
- Bunlar tuning-sonucu değil, ALTYAPI eksikliği → fix küçük ve protokol-dışı
  (single-thread kilidi + hash kayıtları). Reward/env/threshold'a dokunmaz.

## J. Decision
- **B) Küçük reproducibility fix gerekiyor, sonra tuning.** Gerekçe: aynı-seed
  tekrarının KANITLANABİLİR olması full-tuning denetlenebilirliğinin önkoşulu;
  fix (thread kilidi + 3 hash kaydı) düşük riskli ve protokol-dışıdır.
  (A) erken — kanıtlanmamış tekrarlanabilirlikle 50×5 koşmak denetimi bozar;
  (C) gereksiz — tasarım sağlam, eksik sadece kanıt zinciri.
- Fix içeriği (UYGULANMADI): `seed_all`'a single-thread + `PYTHONHASHSEED=0` nocu,
  smoke/tuning scriptlerine equity-curve + action-sequence + model hash kayıtları.

PHASE 4.5 COMPLETE — FIX REQUIRED BEFORE FULL TUNING
