# PHASE 15 — MASTER RESEARCH AUDIT (denetim; deney/fit/backtest YOK)

**Statü:** Kapanış denetimi. Yeni hipotez YOK. Holdout B/C kapalı. Commit yok.
**Yöntem notu:** Aynı hipotez farklı isimle tekrar SAYILMADI. Funding (sinyal /
maliyet-kalemi / carry-tasarımı) ve horizonlar (H12/H48/takvim) ayrı
estimand oldukları için ayrı satırlardadır; M.20 repricing ve 6C-revizyon
koşusu ayrı deney DEĞİL, aynı hattın devamıdır (altta işaretli).

## FAZ DOSYASI (15 alan, terse)

**P1 dry-run infra** — Hip: paper altyapı çalışır. Veri: canlı Binance.
Kapsam: 7+ gün. PIT: N/A (infra). Test: EVET (9/9 verifier). Sadece scout:
hayır (infra). Holdout: yok. Primary: verifier 9/9. Ekonomik: N/A. Cost: N/A.
Risk: yok. İstatistik: 9/9. Verdict: PASS (tek PASS faz). Neden kapandı: çıkış
kriteri sağlandı. Retry: N/A. **Kategori: — (altyapı)**

**P2 walk-forward baseline** — Hip: RSI/SMA kuralı edge üretir. Veri: 18 pair
5m (2020–2023H1). PIT: temiz (tarihsel barlar). Test: EVET (9 fold).
Primary: fold netleri (çoğu negatif: −33.9/−30.5/−26.7…). Ekonomik: FAIL.
Cost: fee 0.001 + 5bps varsayım. Risk: rejim-kırılganlığı betimsel. İstatistik:
fold-tablosu (test-dışı). Verdict: FAIL. Neden: fee-duvarı. Retry: HAYIR
(kural uzayı tüketildi). **Kategori: A**

**P3 FreqAI ML** — Hip: RF + 8 feat H=12'yi öngörür. Veri: BTC 5m. PIT: temiz.
Test: EVET (5 seed + Final A). Primary: Sharpe (−25 hepsi). Ekonomik: FAIL
(15–16k trade, fee ~145 brütü ezdi). Cost: 0.001+5bps. Risk: churn betimsel.
İstatistik: seed-consistency (yön-birliği negatif). Verdict: FAIL (felaket).
Final A TÜKETİLDİ. Retry: HAYIR. **Kategori: A**

**P4 RL (+4.18)** — Hip: PPO policy + decision-level alfa. Veri: BTC 5m
(+artefakt replay). PIT: temiz (7/7 leakage audit PASS). Test: EVET (20 koşu +
4.18 MC/seed + C1–C4). Primary: Sharpe / decision-median-fark. Ekonomik: FAIL
(18/20 saf HOLD; 2 şanslı buy-hold; 4.18 C1/C3 fail). Cost: locked env.
Risk: exposure×drift ayrıştırması. İstatistik: MC p + Welch + power etiketleri.
Verdict: FAIL. Final B ÇALIŞTIRILMADI (korunuyor). Retry: HAYIR. **Kategori: A**

**P5 ML-matrisi** — Hip: 44 hücreden biri FDR-güçlü edge bulur. Veri: BTC 5m/15m.
PIT: temiz. Test: EVET (47 fit). Primary: PSS/edge + gate zinciri. Ekonomik:
FAIL (0/44 q<0.05; en iyi E014 edge −0.69). Cost: C=0.003 kilitli. Risk: WF/seeds
(yol açılmadı). İstatistik: BH-FDR 4 aile + d/power/CI. Verdict: FAIL.
Retry: HAYIR. **Kategori: A**

**6A cross-asset** — Hip: breadth/dispersion/corr incremental bilgi taşır.
Veri: 7 majör 5m (Vision, ücretsiz, tam). PIT: temiz (aynı-saat). Test: EVET
(3 kol). Primary: ΔPSS (−0.000038, CI sıfırı içeriyor). Ekonomik: FAIL
(edge −0.72 ≈ BASE). Cost: C. Risk: WF açılmadı. İstatistik: FDR-3 + 10k
bootstrap. Verdict: FAIL. Retry: HAYIR. **Kategori: A**

**6B funding-sinyal** — Hip: settled funding incremental bilgi taşır. Veri:
fapi fundingRate (~3.8k settlement, tam). PIT: temiz (settlement-sonrası
kuralı). Test: EVET. Primary: ΔPSS (−0.000037, CI sıfır-içerir). Ekonomik:
FAIL (NEW AUC 0.536 = gürültü). Cost: C. Verdict: FAIL. Retry: HAYIR.
**Kategori: A**

**6C OI (STOP→revizyon→koşu)** — Hip: OI incremental bilgi taşır. Veri: Vision
metrics 5m-snapshot (~2020-09+). PIT: temiz (create_time≤close + dedup).
Önce STOP (2023-06-06 venue glitch, 603 VAL-NaN) → R-QC revizyonu (M.20-onaylı)
→ rerun: ΔPSS CI sıfır-içerir, gate FAIL → **FAIL**. Cost: C. Verdict: FAIL
(sinyal hükmüyle; veri-gate'i revizyonda aşıldı). Retry: HAYIR. **Kategori: A**

**P7 H48** — Hip: 4h swing ekonomikleşir. Veri: BTC 5m (aynı). PIT: temiz.
Test: EVET (tek kol + θ_12 comparator). Primary: θ=+5.47 CI [3.58,8.89] —
kırılgan-kuyruk artefaktı (647 event, %1.2 oran, MaxDD 0.963); karşıt-kanıt
θ12=−5.91. Ekonomik: FAIL (PSS<0, d<0.30, q=1.0, MaxDD>0.20). Cost: C.
Verdict: FAIL (exploratory-survival bile YOK). Retry: HAYIR (12h/24h yasaklı).
**Kategori: A**

**P8 cost-scout** — Hipotez YOK (denetim). Karar A: C=0.003 DEFENSIBLE
(20–30bp bandı üstü). Scout-only. **Kategori: — (metodoloji)**

**M.20 futures-repricing** — Aynı H48 sinyali, C≈13.4bp ile: net +0.44%,
θ+8.75 — AMA MaxDD 0.90 + decile-edge 0.75 + kuyruk-kırılganlığı → **B
(zayıf, doğrulama-şartlı)**. Yeni deney DEĞİL (aynı sinyalin muhasebesi).

**M.20-confirm (2025H1)** — Hip: M.20 pozitifi replike olur. Veri: holdout
feather (hash-pinli). PIT: temiz. Test: EVET. Primary: θ=−10.22 CI
[−23.6,+2.99], net NEGATİF, TÜM gate'ler FAIL (AUC 0.5482 bile destek-altı).
Verdict: **FAIL → NOT-CONFIRMED. Bedel: FINAL_P5 TÜKETİLDİ.** Retry: HAYIR.
**Kategori: A** (bağımsız falsifikasyon tamamlandı)

**P9 funding/basis-carry** — Hip: delta-nötr hasat primi toplar. Veri: UM 1h +
funding. PIT: temiz. Test: ÖNCE STOP (statik tasarım 9.58× excursionda tüm
teminat senaryolarında likide). Backtest açılmadı (ölü-tasarım koşulmaz).
Verdict: STOP→CLOSED. Retry: HAYIR. **Kategori: C**

**P10 calendar** — Hip: 3 deterministik kural (weekend/overnight/fade).
Veri: spot 5m (takvim ex-ante). PIT: SINIF-YOK (en güçlü profil). Test: EVET.
Primary: net −0.0021/−0.0028/−0.0030; q=1.0 hepsi; overlap etkisiz. Verdict:
CLOSED (üç FAIL). Retry: HAYIR. **Kategori: A**

**P11 dated-basis** — Hip: quarterly yakınsama primi. Veri: 12 CM kontrat
(tam, yakınsama ±5bp kanıtlı). PIT: temiz. Test: EVET. Primary: net −6.15
BTC; gate'lerden SADECE net_pos/edge/maxdd geçti; Sharpe CI sıfır-içerir,
d=0.079, q=0.39. Verdict: FAIL. Retry: HAYIR. **Kategori: A**

**Scout-only hatlar (deney açılmadı):** P6-7kaynak taraması (karar matrisine
gömüldü) · P12 maker (STOP: veri yok + spot indirimsiz + selection) ·
P13 on-chain (STOP: PIT-tarihçe yok) · P14 mikro-flow (FAST DECAY pilot:
1s'te bile +0.005bp → STOP). **Kategori: D** (PIT/veri-sebebiyle test
edilemedi — özellikle on-chain/L2) — ama P14 pilotu A-yönlü kanıt üretti.

## Kategori özeti

- **A (test edildi, edge yok):** P2, P3, P4, P5, 6A, 6B, 6C, P7, M.20-confirm, P10, P11 (+P14-micro pilot)
- **B (test edildi, ekonomik yetersiz):** — (boş; B-tipi sonuçlar A içinde eridi: hepsi istatistik-gate'leri de geçemedi)
- **C (risk/robustness başarısız):** P9 (sağkalım)
- **D (veri/PIT sebebiyle test edilemedi):** on-chain akışlar, L2 microstructure, maker-fill, news/X arşivi
- **E (scout açık):** YOK (tüm scout'lar hükme bağlandı)
- **F (hiç incelenmedi):** opsiyon-vol primi, çapraz-borsa arb, ETF-akışları (pencere-dışı), miner-döngüsü (güçsüz) — dördü de fizibilite-öncesi elenebilir nitelikte (aşağıda)

## ALPHA COVERAGE MATRIX (özet; tam tablo: ALPHA_COVERAGE_MATRIX.md)

TESTED→tükenmiş: OHLCV, momentum, vol, rejim, funding-sinyal, OI-sinyal,
cross-asset, calendar, futures-basis, trade-flow(micro-pilot), carry(×2),
carpan-etkili... BLOCKED: on-chain, L2, maker-fill, news/X, liquidations.
OPEN: YOK (gerekçeli). F: opsiyon-vol, x-arb, ETF, miner (aşağıda elendi).

## KRİTİK SORU — dürüst cevap: NO

"Mevcut veri + coverage + PIT + ~30bp altında ekonomik test edilebilir
bağımsız alpha var mı?" — **NO.**

Gerekçe zinciri:
1. Ücretsiz/tam/PIT-temiz uzay TÜKENDİ: 11 testli hat (A) + 1 risk-ölümü (C),
   hepsi karar-verici marjlarla (dar CI'lar, q=1.0'lar, negatif netler).
2. Test-edilmemiş uzay ya verisiz (L2 ücretli+duvar-aynı, on-chain PIT-ölü,
   news/X arşivsiz, likidasyon ücretli+seyrek) ya güçsüz (opsiyon/miner/ETF:
   veri-yükü, pencere-uyumsuzluğu, n-kısıtı) ya da aynı-duvarın tekrarı
   (mikro-ufuk: pilotla ÖLÇÜLDÜ, 1s'te bile ~0).
3. YES için gereken 3 aday ÇIKMIYOR: en yakın adaylar (OI-revizyonu: zaten
   koşuldu-FAIL; L2-tedarik: duvar-aynı + ücretli; ETH-kontrol: alfa değil)
   hiçbiri "bağımsız + test-edilebilir + ekonomik-umutlu" üçlüsünü tutmuyor.
4. Dolayısıyla: **ALPHA SEARCH SHOULD STOP UNDER CURRENT CONSTRAINTS.**

## Maliyet notu

C=0.003 kilitli kaldı (P8-A). Venue/maker/BNB indirim yolları repricing
DEĞİL yeni-deney gerektirir — ama aday-hat kalmadığı için bu yolların da
gideceği test YOK. Rescue-tipi öneriler (maker/BNB/coin-değişimi) YASAK
sınıfında değerlendirildi ve elendi.

## SONUÇ: C) STOP ALPHA SEARCH

Sistematik arama yeterince tüketildi; yeni test önermek snooping/rescue
riskine dönüşür. Proje DURDURULMUYOR (altyapı + holdout B/C + M.20 otoritesi
duruyor); ALFA ARAMASI durduruluyor.

VERDICT: STOP ALPHA SEARCH
NEXT: M.20 kapanış onayı + HOLDOUT_REGISTRY finalizasyonu (P5-tüketim kaydı) + faz-kapanış commit'leri (karar user'da)
