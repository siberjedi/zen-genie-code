# PHASE 14 — MICRO-HORIZON DECAY PILOT (aggTrades toxicity, BTCUSDT spot)

**Statü:** TANIMLAYICI pilot. Gate/FDR/p-değeri/model/threshold-opt YOK.
Seçim YOK (5 quantile'ın tamamı raporlu). Holdout kapalı. Commit yok.

## 1. Veri kaynağı

Binance Vision `spot/monthly/aggTrades/BTCUSDT` (resmi public-data deposu;
binance-public-data'da belgeli şema). Kolonlar: agg_id/price/qty/
first-last-tradeId/timestamp/isBuyerMaker.

## 2. Seçilen ay (kilitli, indirme-öncesi)

**2023-02.** Kural: pencere-içi son sakin TAM ay; olay-ayları dışlandı
(Mar-2020, May-2021, Kas-2021, May-2022, Kas-2022, Haz-2023; kamusal tarih,
yön-nötr — sinyal verisi görülmedi).

## 3. Dosya doğrulama / checksum

HEAD 200 (2.62 GB) + `.CHECKSUM` 200; SHA256 eşleşti. Tek ay; başka ay
indirilmedi, başka coin/futures eklenmedi.

## 4. Veri kalite özeti

187.399.566 satır; ts-nonmono 0; 60sn+ gap 0; price/qty≤0 0; NaN 0;
ibm ∈ {True,False}; first/last-tradeId tutarlı. ffill oranı %0.09.
ISSUE YOK — C şıkkı elendi (veri temiz).

## 5. Signal tanımı

Aggressor yönü: isBuyerMaker==false → BUY(+1); true → SELL(−1).
60sn trailing signed-notional + volume-normalize imbalance
(signed/unsigned ∈ [−1,1]); sıralama normalize-imbalance ile; CVD düzeyi
bağlam-only. Tanım 4 ufukta AYNI.

## 6–9. Ufuk sonuçları (n≈484k/quantile; bp)

| h | Q1 | Q2 | Q3 | Q4 | Q5 | spread(Q5−Q1) | rho |
|---|----|----|----|----|----|---------------|-----|
| 1s | −0.0003 | −0.0019 | −0.0020 | −0.0006 | +0.0050 | +0.005 | +0.30 |
| 10s | +0.008 | −0.007 | −0.023 | −0.012 | +0.0363 | +0.028 | +0.10 |
| 1m | +0.086 | −0.007 | −0.059 | −0.059 | +0.0491 | −0.036 | −0.30 |
| 5m | +0.040 | −0.143 | +0.023 | −0.025 | +0.1482 | +0.108 | +0.30 |

Hit-rate'ler 0.48–0.51; medyanlar ~0. Std ufukla büyüyor (0.8→14bp),
ortalamalar ~0'da kalıyor: rastgele-yürüyüş gürültüsü profili.

## 10. Quantile analizi

Monotonik yapı YOK (işaretler ufuklar-arası tutarsız; rho +0.3/+0.1/−0.3/+0.3
salınıyor). En iyi quantile/horizon SEÇİLMEDİ (yasak).

## 11. Decay curve

1s'te bile spread +0.005bp; 5m'de +0.11bp — tamamı 1bp referans çizgisinin
çok altında (30bp'nin ~binde biri). Çürüme-eğrisi çizilemedi çünkü çürüyecek
sinyal YOK (anında-sıfır).

## 12. Cost reference comparison

30/10/5/1bp çizgileri referans-only (grafik: matplotlib yokluğunda
üretilmedi — tablo yeterli). Hiçbir ufuk 1bp'ye yaklaşamadı. Kârlılık
iddiası YOK (yasak).

## 13. Limitations

Tek ay (şubat rejimi); spot-only; last-trade fiyatı (quote/microprice YOK —
bounce gürültüsü muhafazakar yöne iter); ibm-ters-çevrilse bile büyüklükler
aynı mertebede kalır (işaret-bağımsız sonuç).

## 14. Sonuç: A) FAST DECAY (hatta anında-sıfır)

Bilgi 1-saniyede bile pratik olarak yok. Mikro-ufuk çerçevesi de
aritmetik olarak kapalı → tam-deney OTOMATİK AÇILMAZ.

VERDICT: FAST DECAY
NEXT: STOP
