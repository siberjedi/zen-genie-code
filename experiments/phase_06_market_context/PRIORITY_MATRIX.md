# PRIORITY MATRIX — aday sıralaması (araştırmaya göre)

Skor = feasibility skoru (performans tahmini DEĞİL).

| # | Source | New info? | OHLCV'den türetilebilir mi? | Timestamp clean? | Historical coverage (2020→2023H1) | Leakage risk | Acquisition burden | Candidate score |
|---|--------|-----------|------------------------------|------------------|-----------------------------------|--------------|--------------------|-----------------|
| 1 | A Cross-asset | PARTIAL–YES (breadth/dispersion/corr YES) | Kısmen (tek-parite momentum HAYIR) | YES (aynı clock) | TAM (ücretsiz) | LOW | LOW (<500 MB) | HIGH |
| 2 | B Funding | YES | HAYIR | YES (settlement kuralıyla) | TAM (ücretsiz) | LOW (kurala uyulursa) | NEGLIGIBLE | HIGH |
| 3 | C Open interest | YES | HAYIR | YES (kuralla) / günlükte D+1 | Günlük TAM / intraday ücretli | LOW–MEDIUM | LOW (günlük) / MEDIUM (ücretli) | MEDIUM |
| 4 | E Order book (subset) | YES (top-of-book) | HAYIR | YES (asof kuralıyla) | Ücretliyle TAM (2019-12+) | MEDIUM (gap bayraklama) | HIGH (subset) / EXTREME (full L2) | MEDIUM–LOW |
| 5 | D Liquidations | YES | Kısmen (oran paydası) | CONDITIONAL (gecikme beyanı şart) | Ücretliyle (doğrulanacak) | MEDIUM–HIGH | MEDIUM + lisans | MEDIUM–LOW |
| 6 | F News/sentiment | UNCERTAIN | Bilinmiyor | CONDITIONAL | PRATİKTE YOK | HIGH | HIGH + lisans | LOW (REJECT şimdilik) |
| 7 | G X/social | UNCERTAIN | Bilinmiyor | HOLD (survivorship) | Ücretliyle (HOLD) | HIGH | HIGH | LOW (HOLD) |

## Karar ağacı izdüşümü (§22)

- UNAVAILABLE (tarihsel): F arşivi (2020–2023 backfill) → 6F açılamaz.
- HIGH LEAKAGE RISK (belirsiz semantik): predicted-funding, gecikmesiz liq serisi,
  revize-edilebilir agregalar → tasarıma alınmadı.
- FEASIBLE: A, B (hemen); C-günlük (hemen); C-intraday/D/E-subset (koşullu).
- NON-INCREMENTAL: BTC-öz momentum türevleri (6A kapsam dışı bırakıldı).
- HIGH VALUE / HIGH COST: E-full-L2 → implemente edilmez (subset'e inildi).
- Ayrı tutuldu: tüm kaynaklar bağımsız; birleştirme yok.
- Yalnızca güncel veri: `/futures/data/*` (30-gün) → locked pencerelerle
  örtüşmez → kullanılmaz; 2025H1 ile telafi YASAK.
