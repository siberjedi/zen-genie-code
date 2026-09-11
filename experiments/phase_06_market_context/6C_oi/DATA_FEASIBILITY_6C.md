# DATA FEASIBILITY 6C — kapsama / çözünürlük / maliyet

İndirme YAPILMADI. Bulgular dokümantasyon + ayna-kanıt taramasına dayanır;
kesin başlangıç/gap teyidi run-time gate olarak tanımlandı (aşağıda).

## A) Intraday OI — FEASIBLE (ücretsiz, S1 ile)

- **Kaynak:** S1 (Vision daily/metrics), 5m snapshot'lar (`create_time`,
  `sum_open_interest`, `sum_open_interest_value`).
- **Kapsama:** ~2020-09-10 → 2023-06-30 (ayna kanıtı; run-time'da dosya
  varlığıyla teyit). **2020-01-01 → ~2020-09-09 ARALIĞI YOK** → FULL kolu
  train satırları bu aralıkta düşer (~8 ay, train'in ~%30'u; VAL etkilenmez).
  Locked splitler DEĞİŞMEZ; kayıp dropna ile yönetilir ve raporlanır.
- **Z-pencere etkisi:** ör. 30-günlük z-score, efektif başlangıcı ~Ekim 2020'ye
  iter (M.20 lock'ta lookback'lerle birlikte netleşir).
- **Bilinen boşluklar:** OI sütunları tam; oran sütunlarında 2022-Q1 küçük
  boşluklar (OI-only tasarım etkilenmez; oran kullanılacaksa gap politikası lock'a girer).
- **Geceyarısı çift-yazımı:** D günü dosyası `D 00:05 → D+1 ~00:00:02` aralığını
  kapsar; geceyarısı bucket'ı iki dosyada da görünür. **Deterministik dedup
  kuralı zorunlu** (öneri: `create_time` bazında ilk-görüneni tut; lock'ta kilitlenir).
- **Boyut:** 5m snapshot ≈ 105k satır/yıl → 2.8 yıl ≈ 300k satır (<50 MB).
  CPU ihmal edilebilir düzeyde.
- **Stabilite:** resmi arşiv, checksum'lu; yeni günlük dosyalar ertesi gün
  yayınlanır (tarihsel pencere için önemsiz).

## B) Daily OI — 5m/1h tahmin için YETERSİZ (açık hüküm)

Günlük tek snapshot, 5m karar gridine inmez; en fazla rejim-bağlamı olur ki
6C'nin sorusu intraday akıştır. Daily-only tasarıma **karşı öneri**: ya S1
intraday kullanılır ya 6C açılmaz.

## C) Ücretli intraday (S4/S5) — GEREKMEZ (şu an)

S1 varken ücretli kaynağa gerek yok. S1 run-time teyidinde çökerse fallback
sırası: S5 (poll-damga notuyla) → S4 (proof-of-coverage + lisans şartıyla).
Her ikisi de M.20'ye bütçe/lisans kararı gerektirir.

## D) Kontrat sürekliliği (BTCUSDT perp, USDⓈ-M)

Listeleme Eylül 2019 (funding kaynağıyla aynı venue/sembol ailesi); pencere
boyunca delist/kesinti yok (flagship kontrat). COIN-M ile karıştırılmaz;
kilitli sembol BTCUSDT USDⓈ-M'dir.

## E) Ekonomik uygunluk (5m → 1h)

OI akışı (değişim/z-score/divergence) dakika-saat ölçeğinde hareket eder;
1h forward hedefle uyumlu. 8h-kadanslı funding'in aksine OI 5m gridde
yaşar → 5m'e zorlama sorunu YOK. (Sinyal gücü sorusu deneyin işi, bu fazın değil.)

## Run-time gate'ler (STOP koşulları)

1. İlk OI tarihi > 2020-09-30 → STOP (kapsama varsayımı çöktü).
2. VAL (2023H1) içinde OI boşluğu → STOP.
3. Geceyarısı dedup sonrası dup `create_time` → STOP.
4. Sembol/venue dosyası yok → STOP (ikame yok).
