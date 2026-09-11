# PHASE 14 — NEXT ALPHA LINE SCOUT (araştırma; indirme/fit/backtest YOK)

**Statü:** SCOUT. Bulk-download yapılmadı (HEAD propları + doküman taraması).
Feature/backtest/holdout/threshold YOK. Commit yok.

## Aday A) Trade-flow imbalance / CVD (Vision aggTrades)

- **Mekanizma:** aggressor-taraf dengesizliği (isBuyerMaker bayraklı tick
  akış) → kısa-ufuk yön baskısı. Bilgi OHLCV'de YOK (aggressor tarafı).
- **DATA: PASS** — spot + um aggTrades monthly zip'ler 2020-01..2023-06
  HEAD-doğrulamalı (aylık ~100–500MB; tam pencere ~10–15GB/piyasa).
  Kolonlar: aggId/price/qty/first-last-tradeId/timestamp/isBuyerMaker
  (şema run-time'da teyit edilir).
- **PIT/CAUSALITY: PASS** — borsa işlem damgaları; geriye revizyon yok.
- **EXECUTION: FAIL (mevcut çerçevede)** — akademik büyüklükler: 1-dk
  ufukta birim-dengesizlik başına ~0.5–2bp, dakikalar içinde çürüme. Bizim
  h=3 (15dk) diyagnostiğimiz zaten edge≈−0.93 gösteriyor (15-dk taşıma YOK).
  5m/H12/C=0.003 çerçevede aritmetik kapanmaz. 1-dk alt-çerçevede: günlük
  ~144 işlem × taker-maliyet (spot 20bp / futures 8–10bp / maker-futures 4bp)
  ≈ 576–2880bp/gün maliyet vs ~50bp brüt → her dürüst maliyette ölü.
  Maker-futures en iyimser halde bile selection modellenmeden kurgusaldır.
- **NOVELTY: PASS (zayıf)** — aggressor bilgisi OHLCV'de yok; ama eşzamanlı
  getiriyle yüksek korelasyonlu (artık-değer kanıtı gerekir).
- **OVERALL: CONDITIONAL** — koşul: M.20 mikro-ufuk çerçeve-çatalını onaylarsa,
  TEK SONRAKİ ADIM = 1-aylık aggTrades pilot-çekimi + toksisite-çürüme ölçümü
  (1sn/10sn/1dk/5dk; betimsel, gatesiz, FDR-dışı). Pilot, çerçevenin kendisini
  test eder, edge iddia etmez.

## Aday B) L2 book imbalance (Tardis, ücretli)

- **Mekanizma:** top-of-book dengesizliği/spread/microprice (gerçek quote bilgisi).
- **DATA: CONDITIONAL** — Tardis BTCUSDT spot L2 2019-12-01+ dokümante
  (100ms update, top-1000 REST-üretilmiş snapshot, bookTicker 2019-09-21+);
  raw-replay Pro/Business (ücretli, fiyat doğrulanmadı); günlük 300–3000ms
  resub-boşlukları belgeli. Tedarik = M.20 harcama kararı gerektirir.
- **PIT/CAUSALITY: PASS** — WS + local damgalar; boşluklar belgeli yönetilir.
- **EXECUTION: FAIL** — A ile aynı ufuk/maliyet duvarı + kuyruk/latency
  varsayımları (Phase-12 hükmü aynen geçerli; L2 ölçer ama doldurmaz).
- **NOVELTY: PASS** — gerçek quote'lar trade/OHLCV'de yok.
- **OVERALL: CONDITIONAL** (tedarik-gated; A'dan zayıf: ücretli + aynı duvar).

## Aday C) Google-Trends attention proxy

- **Mekanizma:** perakende-dikkat akışı (arama ilgisi → akış).
- **DATA: CONDITIONAL** — ücretsiz ama gayriresmi API; 0–100 normalizasyonu
  pencere-bağımlı (kaçak-tuzağı: sabit-pencere çekimi şart); günlük çözünürlük
  kısa-pencerede, haftalık ötesinde; örnekleme-gürültüsü (tekrar-çekimde değişir).
- **PIT/CAUSALITY: CONDITIONAL** — arama damgası gün/hafta; revizyon/yeniden-
  ölçekleme belgeli pratik.
- **EXECUTION: FAIL** — günlük/haftalık kadans → yılda ~182/52 bahis (güç
  problemi, carry-vakası emsali); zayıf öncül.
- **NOVELTY: PASS (zayıf)** — dikkat ≠ fiyat; ama aktivite-paketi şüphesi.
- **OVERALL: STOP.**

## D) Elenenler (gerekçeli)

- **OHLCV-yapısal "yeniler":** B0–B3 + H3–H720 + L0/L1/L2 + 3 model-ailesi +
  takvim-kuralları uzayı tükendi; kalan her şey yeniden-paketleme veya risk-
  overlay'i (alfa değil). NOVELTY FAIL.
- **Sentiment/news/X:** arşiv/feasibility yok (önceki hükümler geçerli).
- **Liquidation-burst timing:** ücretli + seyrek + OI/funding-null ailesiyle
  aynı duvar.
- **ETF akışları:** pencere-uyumsuz (2024-sonrası).
- **Miner/halving:** bahis-sayısı yetersiz (güç).
- **Opsiyon-vol primi:** veri-yükü + marjin-karmaşası, kapsama-kanıtı yok.

## E) Önerilen tek sonraki deney (M.20 isterse)

**Mikro-ufuk toksisite-çürüme pilotu (A-conditional):** 1-aylık spot aggTrades
çekimi → dengesizlik-CVD serileri → 1sn/10sn/1dk/5dk ileriye-dönük getiri
eğrileri (betimsel; gate/FDR YOK; sonuç ne olursa olsun
tam-çerçeve deneye OTOMATİK GEÇİLMEZ — ayrı M.20 gerekir). Önceki P1–P11'den
farkı: aggressor-verisi hiç kullanılmadı + ölçülen şey edge değil ÇÜRÜME
hızıdır (bilgi-sorusu, iddia değil). Maliyet: ~300MB indirme + saatler-mertebe
hesap.

## Karar gerekçesi (özet)

5m/30bp çerçevede test edilebilir YENİ alfa kalmadı (A'nın çerçevesi
kapanmıyor, B ücretli-aynı-duvar, C zayıf). Dürüst kalan tek yol,
çerçevenin kendisini falsifiye eden sınırlı pilot ya da STOP. Pilot ucuz,
sınırlı ve falsifiye-edici olduğu için CONDITIONAL; tam-deney GO'su için
kanıt YETERSİZ.

VERDICT: CONDITIONAL
NEXT: M.20 mikro-ufuk çerçeve-çatalı kararı; EVET ise tek adım = 1-aylık aggTrades pilot-çekimi + çürüme-ölçümü (gatesiz)
