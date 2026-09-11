# EXPERIMENT OPTIONS — gelecek deney taslakları (LOCK YOK)

Hepsi: BASE (Phase 5 frozen) / NEW-only / FULL (BASE+NEW) üçlü ablation;
metrik ΔFULL−BASE (ΔAUC, ΔrankIC, ΔPSS, Δedge/cost); Phase 5 istatistik
makinesi (PSS t-testi, BH-FDR, 3-seed, WF≥0.60); eşikler değişmez.

## Phase 6A — OHLCV baseline + cross-asset context (ÖNERİLEN İLK)

- **Veri:** Vision 5m klines: ETHUSDT, BNBUSDT, SOLUSDT (2020-08+), XRPUSDT,
  ADAUSDT, DOGEUSDT. BTC feed ile aynı clock.
- **Aday feature yönleri (taslak, üretilmedi):** majör breadth (% yeşil),
  cap-proxy aggregate return, dispersion (std), BTC-majör rolling korelasyon,
  ETH/BTC oranı değişimi. BTC-öz momentum YOK (redundant).
- **Horizon:** 5m/15m/1h — hepsiyle uyumlu (aynı granularite).
- **Leakage:** A1 kuralı; eksik bar düşürme.
- **Maliyet:** < 500 MB indirme, < 2 CPU-saat.
- **Risk:** yüksek korelasyon → incremental Δ küçük çıkabilir (bu da bulgudur).
- **Başarı kriteri:** Phase 5 eşikleri (değişiklik yok).

## Phase 6B — OHLCV baseline + funding (ÖNERİLEN İKİNCİ)

- **Veri:** `/fapi/v1/fundingRate` BTCUSDT, 2020-01-01 → 2023-06-30 (~3.8k satır).
- **Aday yönler:** settled rate (ffill 8h grid), z-score (geçmiş pencere),
  funding × price divergence bayrağı.
- **Horizon:** 8h kadans → 5m'de zayıf beklenti; 1h + rejim bağlamı birincil.
  5m'e zorla uygulama YOK (§17).
- **Leakage:** B1 kuralı (settlement sonrası candle).
- **Maliyet:** ihmal.

## Phase 6C — OHLCV baseline + OI (İKİ KADEME)

- **6C-1 (önce):** Vision daily OI → rejim bağlam feature'ı (D+1 kuralı, C2).
  Maliyet ihmal; beklenti mütevazı (günlük granularite).
- **6C-2 (sonra, opsiyonel):** ücretli intraday OI (Tardis derivative_ticker /
  CoinGlass) → OI değişim, z-score, price/OI divergence. Önce proof-of-coverage
  + lisans + metodoloji notu.
- **Leakage:** C1/C2 kuralları.

## Phase 6D — OHLCV baseline + liquidations (KOŞULLU)

- **Ön-koşul:** CoinGlass (veya eşdeğer) proof-of-coverage 2020→2023H1 5m +
  gecikme beyanı + revizyon politikası + lisans.
- **Aday yönler:** long/short imbalance, burst bayrağı, liq/volume (dikkat:
  payda tanıdık).
- **Horizon notu:** burst'lar seyrek → 5m'de güç düşük olabilir; 15m/1h ile
  birlikte değerlendirilir.
- Bu koşullar sağlanmadan deney AÇILMAZ.

## Phase 6E — OHLCV baseline + order-book subset (KOŞULLU, SUBSET ONLY)

- **Kapsam:** SADECE book_ticker + book_snapshot_25 (Tardis), 5m resample.
  Full L2 replay YASAK derecesinde pahalı (TB) → önerilmez.
- **Ön-koşul:** plan/lisans, storage (~10 GB), gap bayraklama (E1).
- **Aday yönler:** top-of-book imbalance, spread, top-25 depth imbalance.
- **Horizon:** 5m ile uyumlu (mikro-yapı bu horizon'da yaşar).

## Phase 6F / 6G — ŞİMDİLİK YOK

- 6F (news): arşiv erişimi sağlanmadan açılamaz (revisit koşulu §F).
- 6G (X): görev emriyle HOLD; feasibility notu saklı.

## Sıralama mantığı

Tek-kaynak disiplini (§14): önce 6A → raporla → ayrı M.20 kararıyla 6B.
6A ve 6B birbirinden bağımsız; birleştirme YOK.
