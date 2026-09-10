# PHASE 19 — FINAL RESEARCH POSTMORTEM

**Statü:** READ-ONLY SYNTHESIS. Backtest/holdout/FINAL_C erişimi YOK.
Phase 18C geçerli koşum-2 esas alındı (koşum-1 timestamp-unit bug'ı nedeniyle
GEÇERSİZ — performans kanıtı değil).

## 1. Phase 18C DEEP POSTMORTEM (6 aday)

**Sharpe yüksek olmasına rağmen neden PASS olmadı?**
Gates ekonomik/bencmark/stabilite setidir, ham Sharpe değil. #1 (4H SMA200)
Sharpe 1.96 ve #2 2.15 üretti AMA: (a) G4 benchmark excess negatif (−14.7pp /
−10.1pp), (b) G5 aylık stabilite 3/6, (c) G3 WF 4/7, (d) bootstrap p ≥ 0.21
(n=1.092 bar, 6 ay — Sharpe SE ~2.4 yıllıklaştırılmış). "High Sharpe ≠ economic
alpha": Sharpe yüksekliği kısmen vol-target'ın realize-vol'u düşürmesinden
(düşük payda) geliyor; mutlak getiri BH'nin altında.

**Benchmark excess neden negatif?**
2024H1 = +46,5% tek-yönlü bull. Exposure ortalamaları 0,24–0,43 (τ=0,40 kilitli
vol hedefi BTC realize-vol'ünün altında) → stratejiler bull'un ~%65'ini
kaçırdı. Excess: #1 −14,7pp, #4 −16,3pp, #6 −38,0pp.

**Vol-targeting neden BH'yi yenemedi?**
τ=0,40 yıllık hedef, BTC'nin ~%40–60 realize-vol'ünde exposure'ı yapısal olarak
<1 tutar. Crash-avoidance tasarımı (düşük τ) ile bull-benchmark üstünlüğü
(yüksek exposure) aynı anda sağlanamıyor — preregistered G4, bu tasarım
kısıtında bull döneminde neredeyse imkânsız. VT leverage-artifact değil (max 1.0).

**WF stability neden yetersiz?**
4H ailesi 4/7 (2021H1, 2022H1, 2022H2 negatif); 1D SMA50/100 5/7. Edge
dönem-bağımlı: 2020H2 fold'u (+1,10) toplamı domine ediyor.

**2022 crash döneminde mekanizma neden çalışmadı?**
#1: 2022H1 −14,4%, 2022H2 −13,5% (mdd −0,21/−0,22). SMA çıkış gecikmesi +
VT min-exposure 0,25 çukurlarda pozisyonu koruyor → BH'den (−%64) görece iyi
ama mutlak negatif; "crash-avoidance" iddiası fold düzeyinde doğrulanmadı.

**Bull-market opportunity cost?**
2024H1: #1 net +31,8% vs BH +46,5% → ~14,7pp; #4 +21,8% vs +38,0% → ~16,3pp.

**C=.003 vs C=.005?**
G7 hepsi kontrol: #1 1,75, #2 2,10, #4 1,42 (≥0.40 ✓). Cost bu ailenin ölüm
nedeni DEĞİL (turnover 4–31/yıl, maliyet yükü ~%1–9/yıl) — ölüm nedeni
benchmark + stabilite + istatistik.

**FDR neden family-claim'i desteklemiyor?**
p ≥ 0,21 (n=6 ay); 6 testlik aile bütçesi BH q'sunu ≥0,21'e iter; q<0,10 eşiği
hiçbir adayda karşılanmıyor. En güçlü nokta tahmini (Sharpe 2,15) bile 6 aylık
pencereyle istatistiksel olarak sıfırdan ayırt edilemiyor.

**Ayrım (kayıt):** "high Sharpe" (2,15) ≠ "economic alpha" (benchmark'a karşı
negatif, aylık 3/6, FDR q>0,10).

## 2. CROSS-PHASE SYNTHESIS — ortak başarısızlık nedeni

| Hipotez | Değerlendirme | Kanıt |
|---------|--------------|-------|
| Alpha yok (erişilebilir uzayda) | **PARTIALLY SUPPORTED** | 16 testli hat, 0 survivor; ama L2/on-chain/cross-section veri-bloklu (bilinmiyor) |
| Alpha var ama 30bp'de yok oluyor | **SUPPORTED** | P11 brüt ±5bp < C; P3 fee-duvarı; dış literatür 4–10bp kullanıyor (bizim C 3–7×); 18C'de ise brüt bile BH altında |
| Alpha yalnızca çok kısa vadede var | **PARTIALLY SUPPORTED** | P14 1s'te ~0; dış mikro-yapı özellikleri dakikada var ama ücrette yaşamıyor |
| Alpha tail-dependent | **SUPPORTED** | P7 kuyruk-artefaktı; 18C 2020H2-dominant; aylık 3/6 |
| Bull drift yanlışlıkla alpha | **SUPPORTED** | 18C: yüksek Sharpe bull'dan; excess BH'ye negatif; P4: HOLD≈BH en iyisi |
| Risk-adjusted edge yok | **SUPPORTED** | P5 0/44 FDR; 6A/B/C CI∋0; P10 q=1.0; 18C FDR q>0.10 |
| Benchmark selection problem | **PARTIALLY SUPPORTED** | BH bull'da acımasız; ancak G4 preregistered — tanımlı benchmark altında gerçek fail |
| Turnover problem | **SUPPORTED** (5m ailelerinde) | P3 15–16k trade; P14; 18C'de değil (4–31 trade/yıl) |
| Execution problem | **PARTIALLY SUPPORTED** | maker verisi yok (P12); taker varsayımı C=0.003'te kapsamlı testli |
| Data/PIT problem | **SUPPORTED** (bloklu ailelerde) | on-chain PIT-ölü, L2 ücretli, news/X arşivsiz |

**Ortak neden:** Er coin'lerdeki (2013–2020) gerçek yapısal primi — yüksek
volatilite + yavaş bilgi yayılımı — 2020–2024 döneminde kurumsal
arbitraj/piyasa yapıcılığı eritti; 30bp takas maliyeti + tail-riski, kalan
zayıf sinyallerin tamamını aşıyor. Tek başarılı "alpha" kategorisi: hiçbir şey
yapmamak (HOLD/P4) — yani beta.

## 3. STRONG NEGATIVE EVIDENCE

- **A) Predictive failure:** P5 0/44 q<0.05 · M.20-confirm AUC 0.5482 (holdout-kararlı) · 6B AUC 0.536 · P10 q=1.0 · 6A/6C ΔPSS CI∋0
- **B) Economic failure:** 18C G4 hepsi negatif excess · P11 net −6.15 BTC · P9 9.58× likidasyon · P7 MaxDD 0.963
- **C) Cost/turnover:** P3 (16k trade, fee 145 brütü ezdi) · P14 (1s'te +0.005bp) · dış: Frontiers 2026 "hiçbir strateji ücrette yaşamıyor"
- **D) Benchmark failure:** 18C (6/6 aday BH'ye kaybetti) · P4 (18/20 HOLD — BH'yi geçemeyen karar)
- **E) Drawdown:** P7 0.963/0.90 · P9 likidasyon · 18C 2022 foldları negatif
- **F) Stability:** 18C aylık 3/6, 4H WF 4/7 · P7 θ12=−5.91 · P11 d=0.079
- **G) Data/PIT:** P13 on-chain PIT-ölü · L2 ücretli · P12 maker verisiz

## 4. SURVIVING UNKNOWN SPACE ("NOT TESTED ≠ PROMISING")

| Alan | Data req | Cost | PIT zorluk | Beklenen edge | Araştırma maliyeti | Bilgi değeri |
|------|----------|------|-----------|---------------|--------------------|--------------|
| L2/order-book | ücretli (yüksek) | yüksek | orta | düşük-or ta (dış: BTC'de null, ETH-dominant) | yüksek | orta |
| Maker execution | kendi fill log'u | yok | yok | bilinmiyor (maliyet-i̇ndirimi) | yüksek | düşük (sinyal değil) |
| On-chain PIT | 2024+ yalnız | orta | **çok yüksek** (2020-23 backtest imkânsız) | bilinmiyor | yüksek | düşük |
| Options vol yüzeyi | Deribit ağır | yüksek | orta | zayıf (F) | çok yüksek | düşük |
| Cross-exchange arb | çok-venue HF | orta | yüksek | düşük (2026 verimli) | çok yüksek | düşük |
| **Haftalık cross-sectional long-only** | **Mevcut (coldstorage 6A + funding + OI)** | **düşük** | **düşük** | orta (dış: weekly flow Sharpe 1.93; ama 30–3000 coin literatürü vs bizim 7 majör) | **düşük-orta** | **en yüksek** |

## 5. FINAL RESEARCH THESIS

**NEGATIVE KNOWLEDGE:** 16 hipotez-ailesi karar-verici gate'lerde başarısız
(P2–P18C; 0 survivor). 30bp round-trip maliyet, erişilebilir tüm sinyalleri
aşıyor. Kısa-ufuk mikro yapı istatistiksel olarak var ama ekonomik değil.
Crypto'da "yüksek Sharpe" çoğunlukla bull-drift + düşük-vol paydasından geliyor;
benchmark'a karşı excess'te eriyor. Edge'ler tail-dependent ve dönem-bağımlı;
holdout'la (M.20, 18C) doğrulanan hiçbir sinyal yok.

**POSITIVE KNOWLEDGE:** Uzun-only trend + vol-target risk-azaltıcıdır
(18C: MaxDD −12% vs BH −22%) ama ekonomik alpha değildir (G4). P5/P7/P11
karar-verici marjlar üretti (dar CI'ler, q=1.0'lar) — "sinyal yok" hükmü güçlü.
Altyapı: M.20-emsal holdout protokolü (pin+registry+tek değerlendirme),
preregistration, FDR disiplini, `to_ms` unit-güvenliği, C=0.003 maliyet
scouting'i — hepsi çalışır durumda ve tekrar kullanılabilir. Dış literatürle
tutarlılık: mikro-yapı ücret-ölümü (Frontiers 2026), 4h trend'in BH'yi
yenebileceği iddiası (iolufemi 2026) bizim FINAL_B'de G4 benchmark gate'inde
doğrulanmadı — dış sonuçların çoğu 4–10bp maliyet varsayımıyla.

**UNKNOWN:** L2'nin BTC'deki gerçek değeri; maker fill avantajı; on-chain
PIT-tarihçesi; haftalık cross-sectional long-only'nin 7 majör + 30bp altında
davranışı; options vol primi.

**VERDICT: RESEARCH STOP — aşağıdaki karar dokümanında gerekçeli.**