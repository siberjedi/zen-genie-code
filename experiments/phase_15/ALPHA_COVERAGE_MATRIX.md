# ALPHA COVERAGE MATRIX (tablo-only; yorum: PHASE_15_MASTER_AUDIT.md)

| # | Alan | Durum | Kanıt (kısa) |
|---|------|-------|--------------|
| 1 | OHLCV / price structure | TESTED→EXHAUSTED | P3/P5 B0–B3; en iyi AUC 0.68, edge<0 |
| 2 | momentum / trend | TESTED→EXHAUSTED | ret_*/SMA/EMA; H12–H72 ufuklar; q=1.0 |
| 3 | volatility | TESTED→EXHAUSTED | ATR/rv/roll_std/vol-pct; destek-metriği bile geçemedi |
| 4 | regime | TESTED→EXHAUSTED | ADX/vol-rank + 4.14 classifier + 4.18 stratifikasyon |
| 5 | funding (sinyal) | TESTED→EXHAUSTED | 6B: NEW AUC 0.536; ΔPSS≈0 |
| 6 | open interest (sinyal) | TESTED→EXHAUSTED | 6C revizyon-koşusu FAIL (veri-gate'i aşıldı, sinyal yok) |
| 7 | cross-asset | TESTED→EXHAUSTED | 6A: FULL≈BASE (AUC 0.68/0.68), Δ≈0 |
| 8 | calendar/session | TESTED→EXHAUSTED | P10: 3 kural net<0, q=1.0 hepsi |
| 9 | futures basis | TESTED→EXHAUSTED | P11: net −6.15 BTC, q=0.39, d=0.079 |
| 10 | on-chain akış | BLOCKED | PIT-tarihçe yok (Glassnode PIT 2024+; CQ non-PIT belgeli) |
| 11 | sentiment/news/X | BLOCKED | arşiv/feasibility yok; X-layer boş |
| 12 | trade-flow / aggTrades | TESTED(pilot)→EXHAUSTED | P14: 1s'te bile +0.005bp; 187M trade |
| 13 | L2/order-book | BLOCKED | ücretli veri + aynı ufuk-duvarı |
| 14 | liquidation flow | BLOCKED | ücretli + seyrek + null-ailesi |
| 15 | options vol primi | F (incelenmedi) | veri-yükü + marjin-karmaşası; kapsama-kanıtı yok |
| 16 | ETF/makro akış | F (incelenmedi) | pencere-dışı (2024+) / fazla-yavaş |
| 17 | execution/maker edge | STOP (P12) | spot indirimsiz + selection modellenemez |
| 18 | carry (funding+basis) | TESTED→EXHAUSTED | P9 likidasyon-ölümü; P11 negatif |
| 19 | market-neutral | TESTED→EXHAUSTED | carry via P9/P11; bağımsız formu kalmadı |
| 20 | diğer bağımsız alpha | YOK | aday havuzu boş (yukarıdaki eleme sonrası) |

Lejant: TESTED = karar-verici test koştu · BLOCKED = veri/PIT engeli ·
EXHAUSTED = çerçevede tekrarı yasaklı · F = fizibilite-öncesi elenebilir.
