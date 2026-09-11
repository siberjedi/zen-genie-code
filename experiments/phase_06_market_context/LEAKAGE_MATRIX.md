# LEAKAGE MATRIX — data time / publication / availability / decision ayrımı

Karar anı (varsayılan): 5m candle close. Kural: `availability_time ≤ decision_time`.

## B1) Funding settlement serisi

- Event: 8h funding dönemi kapanışı (00:00 / 08:00 / 16:00 UTC).
- Data time: [T−8h, T] premium TWAP dönemi.
- Publication: T anında (settlement ile birlikte kesinleşir).
- Availability: T.
- **Kural:** fundingTime=T değeri yalnızca close ≥ T olan candle'larda feature
  olur. T'den önceki candle'a yazmak = LEAK (dönem kapanmadan oran bilinemez).
- Predicted/intraperiod funding kullanılırsa: o anki mark/index'ten hesap
  formülü dondurulmalı ve formülün o tarihteki borsa metodolojisiyle aynı olduğu
  kanıtlanmalı. Aksi halde HIGH LEAKAGE RISK → önerilmez.

## C1) OI değişim / z-score (intraday)

- Data time: bar [t−w, t] (yalnızca geçmiş pencere).
- Publication/availability: exchange push + poll gecikmesi (saniyeler).
- **Kural:** OI[t] değeri close=t candle'ına yazılabilir (o ana kadar yayınlanmış
  değerler). Z-score penceresi [t−w, t]; w-içi gelecek YOK.
- Tardis local_timestamp kullanılıyorsa: bar ataması asof-join ile geriye
  (backward), asla ileriye yuvarlama yok.

## C2) Günlük OI (Vision metrics)

- Data time: UTC günü. Availability: ertesi gün dosya yayını.
- **Kural:** D gününe ait günlük OI, D günü içindeki candle'larda KULLANILMAZ;
  ilk kullanım D+1 günü. Aksi = LEAK (gün kapanmadan gün-sonu değeri bilinemez).

## D1) Liquidation aggregates (CoinGlass)

- Data time: aralık [t−Δ, t]. Publication: sağlayıcı işlem gecikmesi (dakikalar?).
- **Kural:** sağlayıcının gecikme beyanı alınır; feature timestamp'i
  `interval_end + max_beyan_gecikme` olarak kaydırılır (konservatif).
  Gecikme beyanı yoksa HIGH LEAKAGE RISK.
- Revizyon: sağlayıcı geçmişi revize ediyorsa seri kullanılmaz (o tarihteki
  karar-anı değeri yeniden üretilemez).

## E1) Order-book top-of-book

- Data time: tick anı. Availability: tick anı (+ms).
- **Kural:** 5m bar'a yalnızca close'tan önceki son snapshot (asof). Bar-içi
  gelecek tick'lerden türetilmiş hiçbir istatistik (örn. bar-içi max imbalance)
  feature OLAMAZ — o istatistik close anında bilinemezdi.
- Re-subscribe gap (~300–3000ms/gün) ve generated-snapshot günleri işaretlenir;
  o barlar düşürülür (doldurma yok).

## F1) Haberler

- Data time: olay anı. Publication: yayın anı (+gecikme). Availability:
  publication + indeksleme gecikmesi (sağlayıcıya göre dakika–saat).
- **Kural:** feature anı = availability_time; decision_time ≥ availability_time.
  Sağlayıcı gecikme beyanı yoksa kullanılmaz.
- Duplicate/syndication: aynı haberin ikinci yayını yeni sinyal DEĞİL;
  dedup anahtarı (URL-canonical + ilk-görülme) zorunlu.
- Future contamination: arşivden çekilen makalede "sonradan güncellendi"
  damgası varsa orijinal yayın anı kanıtlanmadan kullanılmaz.

## G1) X / social — HOLD

- Yukarıdaki F1 kurallarına ek: silinme/suspend sonrası corpus değişir →
  bugün çekilen 2021 verisi, 2021'deki karar-anı evreniyle aynı DEĞİL
  (survivorship). Düzeltme geriye dönük imkansız → bu fazda kullanım YOK.

## A1) Cross-asset klines

- Data/publication/availability: BTC feed ile aynı exchange clock; aylık
  dosya yayını geriye dönük olduğu için karar-anı sorunu YOK (tarihsel barlar
  o tarihte de mevcuttu).
- **Kural:** her sembol kendi close zamanına hizalanır; eksik bar ileri
  doldurulmaz (o 5m dilimi düşürülür veya bayraklanır).

## Genel yasaklar

- İleri-yuvarlama (ceil) ile bar atama YOK.
- "Tahmini kesin değer" (predicted funding, prelim OI) kesin seri gibi YOK.
- Revize edilebilir üçüncü-parti seri, revizyon-dondurulmuş snapshot olmadan YOK.
