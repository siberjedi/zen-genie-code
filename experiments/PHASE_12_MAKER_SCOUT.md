# PHASE 12 — MAKER EXECUTION SCOUT (araştırma; kod/backtest YOK)

**Statü:** SCOUT. Backtest/fit/onay/commit YOK. Holdout B/C kapalı.

## Veri envanteri (doğrulanmış)

- Mevcut: 5m + 1h OHLCV mumları, funding settlement'ları, OI 5m snapshot'ları,
  günlük metrikler. Fee tarifeleri (dokümante).
- **Mevcut OLMAYAN:** bid/ask quote serisi, L2 depth, trade-level prints,
  maker fill kaydı, queue pozisyonu, latency ölçümü (repo-taraması negatif).
- Execution-cost altyapısı: Phase 8 bandı (20–30bp, C=0.003 üst-taraf),
  Phase 3.6 hysteresis bulgusu (churn 22x kesilir ama gross da erir).

## Araştırma bulguları

1. **Simüle edilebilirlik:** HAYIR — güvenilir şekilde yok. Mum-verisiyle
   maker simülasyonu (örn. "low ≤ bid ise doldu") doldurma-olasılığını varsayar;
   varsayım test edilemez (yer-verisi yok).
2. **Mikroyapı verisi:** YOK (yukarıda).
3. **Mum-bazlı maker backtest savunulabilirliği:** confirmatory kanıt olarak
   HAYIR. Momentum-sinyallerde (bizim aile: AUC>0.5 long top-decile) pasif
   dolumlar sistematik olarak aleyhe seçilmiştir: dolum, fiyat size karşı
   hareket ettiğinde gelir. Mum-proxysi bu maliyeti SIFIRLAR → iyimser-yanlı.
   En fazla optimistic-bound (tek-yönlü falsifikasyon) olarak kullanılır.
4. **Maker gerçekte neyi azaltır:** SPOT regular'da fee indirimi YOK
   (maker=taker=%0.10) — yalnızca yarım-spread (~0.1–0.5bp) kazanılır, buna
   karşılık selection + non-execution eklenir (net negatif beklenir).
   Futures'ta ~6bp fee tasarrufu GERÇEK (10bp→4bp) ama venue-değişimi
   (basis/funding modellemesi = yeni deney) + selection modellenmemiş kalır.
5. **Modellenecek riskler (verisiz modellenemez):** fill olasılığı, partial
   fill, adverse selection (sinyal yönünde en büyük), missed-fill fırsat
   maliyeti, kuyruk/latency. Hepsi serbest parametre → tuning yüzeyi →
   protokol ruhuna aykırı. REDDEDİLDİ.
6. **Sinyal-ailesini maker altında retest:** SPOT'ta anlamsız (fee indirimi
   yok; 60–90bp'lik açık sub-bp spread ile kapanmaz). Futures-maker aritmetik
   sınırı (H48 event ~+%0.50 net) KURGUSALDIR (selection sıfırlanmış varsayıldı);
   test etmek sahte-PASS üretir — tehlikeli, değersiz. MaxDD/kuyruk sorunları
   maliyet-varsayımından bağımsız sürer.
7. **Yeni ekonomik hipotez mi?** HAYIR. Maker, aynı sinyallerde maliyet
   mühendisliğidir; bağımsız alfa kaynağı değildir. "Edge" execution
   becerisi gerektirir (HFT altyapısı bizde YOK).

## 8. Hüküm: C) STOP

Mevcut veriyle güvenilir maker testi yapılamaz; sentetik varsayımla sahte
edge üretilmedi. Optimistic-bound aritmetiği (yukarıda) yalnızca teorik tavanı
niceler (~+%0.5/trade, selection-harici) — kanıt DEĞİLDİR.

## Ek: önerilen Phase-12 deney tasarımı (M.20 isterse; ŞU AN AÇILMIYOR)

- **Veri:** L2/tick arşiv tedariki (örn. Tardis: TB-mertebe, ücretli) + canlı
  paper-fill ground-truth'u. Bunlar OLMADAN deney YOK (önkoşul gate'i).
- **Execution modeli:** kuyruk-simulasyonu (quote + depth + latency varsayımlı,
  hepsi preregistered) + adverse-selection raporu (dolum-sonrası drift).
- **Maliyet:** venue-gerçek fee + spread-crossing YOK (maker) + modellenmiş
  selection + missed-fill fırsat maliyeti.
- **Falsifikasyon:** selection-dahil net ≤ 0 → FAIL; ayrıca canlı-paper
  simülasyon sapması > tolerans → model REDDEDİLİR (sayı lock'ta).
- **Gate'ler:** net>0, edge≥1.2, MaxDD≤0.20, q<0.05 (tek familya), power≥0.80.
- **Holdout planı:** B/C kapalı; final-confirmation için YENİ pencere (P5
  tüketildi) + canlı-paper zorunlu; ayrı M.20 ister.
- **Fark:** P1–P11'in hiçbiri execution-becerisini test etmedi (hepsi
  taker-varsayımlı sinyal testleri). Bu, sinyal DEĞİL icra-hipotezidir —
  ancak yukarıdaki veri-önkoşulu sağlanmadan açılamaz.

---
*Kod değişikliği yok. Yeni faz çalıştırılmadı.*
