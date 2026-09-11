# PHASE 8 — EXECUTION / COST FEASIBILITY SCOUT (araştırma; backtest YOK)

**Statü:** SCOUT. Backtest/fit/holdout/M.20 değişikliği/commit YOK.
**Soru:** C=0.003 round-trip varsayımı gerçekçi Binance execution'ında
savunulabilir mi? (Phase 7 sonucu değiştirilmez; aralık sonuç-kurtarma için
seçilmedi — C deneylerden ÖNCE kilitlendi.)

## 1. Binance fee yapısı (regular user)

- **Spot:** maker/taker %0.10 (10bp) her yön; BNB ile ödeme %25 indirim →
  %0.075. Deney dönemi (2020–2023) boyunca standart tarife buydu.
- **USDⓈ-M futures:** maker %0.02 (2bp), taker %0.04→%0.05 (dönem içinde
  4bp yaygındı, güncel 5bp); BNB %10 indirim (futures).
- **Zero-fee BTC spot promo:** 8-Tem-2022 → 22-Mar-2023 arasında BTC/USDT dahil
  13 paritede maker+taker SIFIR; sonra TUSD-only. VAL'in ~80 günü bu rejimdeydi —
  ancak geriye-dönük periyot-fiyatlama post-hoc olur (aşağıda §7 notu).
- **Funding (perps):** ayrı maliyet; 8h settlement, ort ~1bp/8h, kuyruk riski
  yüksek. Deneyde modellenmedi (spot fiyatlar kullanıldı).

## 2. C=0.003 ayrıştırması (30bp round-trip)

`C = fee 0.001×2 (20bp) + slip 5bps×2 (10bp)`; spread ayrı kalem DEĞİL
(slippage içinde varsayıldı).
- **Deterministik:** borsa fee tarifesi (dönem-boyunca bilinen).
- **Koşullu:** spread (0.1–1bp BTCUSDT top-of-book; sakinken ihmal, hızlı
  barda büyür), slippage (boyut+hız rejimine bağlı), funding (perps'te).

## 3. BTCUSDT gerçekçi aralık (5m sinyal / 4h tutuş, küçük boy, regular)

- Sakin-bar market impact: ~0–2bp/yön; sinyal-barları (momentum-seçilimli)
  hızlı rejimde → slip dağılımının SAĞ kuyruğunda işlem beklenir.
- 5bps/yön varsayımı: sakin piyasa için CÖMERT (muhafazakar), sinyal-barları
  için GERÇEKÇİ-hafif. Ortalamada makul merkez.

## 4. Spot vs perpetual (ayrı)

- **Spot-taker:** 20bp fee + spread/slip → ~20–25bp gerçekleşme bandı.
- **Perps-taker:** 8–10bp fee + funding (~0.5bp/4h beklenen, sivri kuyruk) +
  spread/slip → ~10–16bp bandı. AMA: deney spot fiyatlarla kuruldu; baz riski
  + funding rejimi modellenmeden venue değiştirilemez (yeni M.20 gerekir).

## 5. Maker varsayımı sorunları (neden iyimser kalır)

Sinyal-takipçi emir bekleyemez (missed fills); kuyruk pozisyonu + adverse
selection: dolan limit emirler sistematik olarak aleyhe seçilmiştir (Lehalle–
Mounjid: dolum-hızı/fiyat-iyileşmesi takası + latency erozyonu; maker-taker
literatürü: yüksek-rebate venue'lerde düşük fill-rate + uzun kuyruk maliyeti).
Modellenmemiş maker-maliyeti nominal fee'den (spot 15–20bp, futures 4bp)
tipik olarak YÜKSEKTİR → maker-bazlı alt-maliyet iddiası REDDEDİLİR.

## 6. Taker varsayımı bileşenleri

Fee (deterministik, yukarıda) + spread-crossing (~yarım-spread, sub-bp) +
slippage (koşullu, sinyal-barlarında yukarı-yanlı). C'nin 10bp slip payı bu
üçünü topluca ve muhafazakarca karşılar.

## 7. Tarih karıştırma yasağı (uygulandı)

Güncel tarife (futures taker %0.05) dönem tarifesiyle (%0.04 ağırlıklı)
karıştırılmadı; fark ~2bp/round-trip — sonucu değiştirecek mertebede değil.
Zero-fee penceresi (VAL'in bir kısmı) periyot-fiyatlama gerektirir + wash-trade
nüansları taşır → kilitli C'ye geriye-dönük uygulanamaz (ayrı M.20 + ayrı
deney gerekir).

## 8. Defensible cost range (tek aralık; sonuçtan bağımsız)

**Deney-olarak-koşulan yapı için (spot, close-execution, regular, küçük boy,
2020–2023): 20–30bp round-trip.** C=0.003 (=30bp) bu bandın ÜSTÜNDEDİR:
muhafazakar-taraflı ama savunulabilir (taker + hızlı-bar slip payı).
Alt rejimler mevcuttur (BNB-spot ~15–20bp; perps-taker ~10–16bp) ancak her
biri kayıt-dışı varsayım/venue-değişimi ister → repricing DEĞİL, yeni deney.

## 9. Breakeven sanity check (backtest DEĞİL)

Phase 7 gross +0.2342% (0.002342). Net>0 ⟺ C < %0.2342 (23.42bp).
- C=30bp → net −0.0658% (kilitli sonuç, değişmez).
- 20–30bp bandının alt ucu bile (+3bp) marjinal; perps-taker ~12–16bp
  teoride +7–11bp bırakır — AMA selection/slip/funding-kuyruğu öncesi ve
  venue-değişimi gerektirir. Hiçbir dürüst varsayım stratejiyi AÇIKÇA
  ekonomik yapmaz.

## 10. Karar

**A) C=0.003 DEFENSIBLE → maliyet varsayımı korunur; execution maliyeti
stratejinin temel darboğazıdır.**

Gerekçe: bant-içi üst-taraf, taker-gerçekçi, maker-iyimserliğine kapalı,
tarih-karıştırmasız. B (daha düşük rejim) ancak yeni M.20 + yeni deneyle
(zaten §8'de yolu açık); C (yetersizlik) kanıtı yok — hızlı-bar slip'i
yukarı risk taşır ama bandı deldiği gösterilemedi; D'ye gerek yok (bant
tanımlanabildi). Phase 7 FAIL değişmez.

**READY FOR M.20 DECISION**
