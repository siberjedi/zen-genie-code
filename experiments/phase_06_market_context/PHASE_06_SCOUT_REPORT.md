# PHASE 06 — SCOUT REPORT (morning review)

**Tarih:** 2026-09-08 · **Tür:** research scout (training/tuning/backtest YOK)
**Karar:** **A) READY FOR PHASE 6 EXPERIMENT DESIGN** (deney çalıştırılmadı; lock yok)

## 1. Phase 5 → Phase 6 rationale

Phase 5 (44 cell, 0 FDR): en iyi hücre E014 AUC 0.679 / dir-acc ~0.77 /
rank-IC 0.043 ama PSS −0.00207, edge/cost −0.69. Phase 4.18: decision-level
edge yok, RL ≈ exposure × drift. Sonuç: model aramak değil, **bilgi aramak**
gerek. Bu faz "hangi kaynak geçerli şekilde test edilebilir?" sorusunu cevaplar;
"hangi kaynak çalışır?" sorusunu cevaplamaz.

## 2. Candidate sources & evidence

| # | Kaynak | Kanıt (2026-09-08 taraması) | Skor |
|---|--------|------------------------------|------|
| 1 | A Cross-asset | Vision monthly klines, 5m, checksum'lı, 2017/2020+, ücretsiz | HIGH |
| 2 | B Funding | `/fapi/v1/fundingRate`, 1000/page, BTCUSDT ~Eyl-2019+, 8h settlement, ücretsiz | HIGH |
| 3 | C OI | Resmi REST 30-gün (backfill imkansız); Vision daily metrics (günlük); intraday ücretli | MEDIUM |
| 4 | E Book-subset | Tardis BTCUSDT L2 2019-12-01+, ücretli ($350/ay+), TB-ölçek; subset (ticker/top25) feasible | MEDIUM–LOW |
| 5 | D Liquidations | Resmi arşiv yok; CoinGlass 1m–5m ücretli planlarda, 2019 iddiası doğrulanacak | MEDIUM–LOW |
| 6 | F News | CryptoPanic free API kalktı (04/2026); Growth 1-ay, Enterprise 1-yıl cursor-only → 2020–2023 backfill yok | LOW |
| 7 | G X | Pay-per-use ($0.005/read, cap) / twitterapi.io ($0.00015/tweet); survivorship + HOLD emri | LOW |

## 3. Timestamp risks (kritik)

- Funding: yalnızca settlement-sonrası candle (B1). Dönem-içi değer LEAK.
- OI-günlük: D günü D'de kullanılmaz, D+1'de (C2).
- Liq: sağlayıcı gecikme beyanı + kaydırma şart (D1); revizyonlu seri yasak.
- Book: asof-join geriye; bar-içi türev istatistik yasak (E1).
- Haber/sosyal: availability_time kuralı + dedup + contamination kontrolü.
- `/futures/data/*` 30-gün serileri locked pencerelerle örtüşmez → yok hükmünde.

## 4. Coverage

Locked Train/Val (2020-01-01 → 2023-06-30): A TAM, B TAM, C-günlük TAM,
C-intraday/D/E-subset ÜCRETLİ-DOĞRULANACAK, F YOK, G HOLD. 2025H1 telafi YASAK.

## 5. Acquisition burden

6A <500 MB/<2 CPU-saat; 6B ihmal; 6C-günlük ihmal; 6C-intra/6D MB'lar+lisans;
6E-subset GB'lar/~10 GB storage; 6E-full TB'lar (önerilmez).

## 6. Incremental information assessment

YES: funding, OI-akışı, liq-imbalance, top-of-book. PARTIAL: breadth/dispersion/
corr-regime (YES'e yakın), tek-parite returnler (redundant şüphesi).
UNCERTAIN: news skoru, sosyal aggregate'ler. NO: BTC-öz momentum türevleri.

## 7. Priority ranking

1. Cross-asset (HIGH) → 2. Funding (HIGH) → 3. OI (MEDIUM) →
4. Book-subset (MEDIUM–LOW) → 5. Liquidations (MEDIUM–LOW) →
6. News (LOW) → 7. X (LOW/HOLD).

## 8. Recommended first experiment

**Phase 6A** (cross-asset context): ücretsiz, tam coverage, timestamp-clean,
horizon-uyumlu (5m/15m/1h). İkinci sırada **6B** (funding, 1h/rejim ağırlıklı).
Tek-kaynak disiplini: 6A bitmeden 6B'ye geçilmez; birleştirme yok.

## 9. Alternatives

Bütçe/lisans varsa: 6C-1 (günlük OI, bedava) 6A'ya paralel DEĞİL, sonrası aday.
Ücretli yolda önce proof-of-coverage istenenler: 6C-2, 6D, 6E-subset.

## 10. What NOT to do

- Phase 5'te reddedilen model/label/horizon'ları yeniden açma.
- Kaynakları tek feature set'te birleştirme.
- 5m'e uymayan kadansı (funding 8h, günlük OI) 5m'e zorlama.
- Predicted-funding / prelim-OI / revize seri kullanma.
- F/G arşivi "bir şekilde bulunur" varsayma.
- 2025H1/B/C/A'ya dokunma; 2025H1 indirme.
- Sonuç görmeden "şu kaynak kesin çalışır" deme.

## 11. Protocol impact

Yeni threshold YOK, lock YOK, config değişikliği YOK. Tek gereken: M.20 ile
GATE-2 kararı (hangi TEK deney). FDR aile yükü not edildi (az kol önerisi).

## 12. Required M.20 decisions

1. 6A lock (kapsam: sembol listesi, feature yönleri, horizonlar)?
2. Ücretli veri bütçesi var mı (6C-2/6D/6E için üst sınır)?
3. 6B'nin 6A'dan bağımsız ikinci deney olarak takvimi?

## 13. Estimated compute / data size

Tablo için DATA_FEASIBILITY.md son bölümüne bak (6A <2 CPU-saat … 6E-subset orta).

## 14. Stop-condition log

STOP tetiklenmedi: 2025H1/B/C/A erişimi YOK, training YOK, threshold YOK,
fishing YOK, protocol conflict YOK.

## 15. Holdout final check

- [x] 2025H1 untouched
- [x] Final B untouched
- [x] 2024H2 untouched
- [x] Final A untouched
- [x] no training
- [x] no tuning
- [x] no backtest
- [x] no final test
- [x] no feature selection
- [x] no protocol lock
- [x] no new thresholds
- [x] no fishing

**READY FOR MORNING REVIEW**
