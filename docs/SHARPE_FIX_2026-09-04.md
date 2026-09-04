# Sharpe Metrik Düzeltmesi — 2026-09-04

## Özet
`src/data/metrics.py:5` ve çağrıldığı yerler (`src/backtest/evaluate.py:18` ve `dashboard/backend/app.py:892`) 2026-09-04 öncesi **per-trade** `profit_ratio` serisini doğrudan `periods_per_year=365` ile annualize ediyordu. `365` sadece **günlük** return için doğru. Trade frekansı günlükten farklı (ör. 19 trade / 8 gün = 866 trades/year) → `sqrt(365)` yanlış.

## Mevcut Kullanım (Hatalı)
- `evaluate.py:15` `returns = df["profit_ratio"]` (16 trade, 4 güne yayılmış)
- `metrics.sharpe(returns, 365)` → `mean 0.0065 / std 0.0215 * sqrt(365) = 5.83` (dashboard `statistics.pstdev` ile 6.02)
- `dashboard app.py:891` `rets=[close_profit]` (per-trade) + `sqrt(365)` → aynı hata

**Seri:** trade return (per-trade), **periods:** 365 (günlük varsayımı) → **mismatch**.

## Doğru Yöntem
`config/experiment.yaml:15` `sharpe_annualization: 365` kripto için **günlük** (7/24) → Sharpe **günlük** return üzerinden hesaplanmalı.

- `close_date` varsa: günlük aggregate `daily = groupby(date)["profit_ratio"].sum()` → 0-filled takvim günleri → `sharpe(daily, 365)`
- Yoksa: `trades_per_year = n_trades / (days/365)` → `sharpe(per_trade, tpy)`

**Örnek DB (16 kapalı trade, 4 gün):**
- Yanlış (per-trade+365): 5.83 (dashboard 6.02 pstdev)
- Doğru günlük+365: 11.39–14.46 (daily mean 0.008865, std 0.0117, 4 gün)
- Doğru per-trade+tpy (1460): 11.66

Hepsi farklı; eski 6.02 **güvenilir değil**, sessizce overwrite edilmedi.

## Değişiklikler (Primary metric aynı: `oos_sharpe_ratio`)
- `src/data/metrics.py:1` dokümantasyon + uyarı eklendi, imza aynı.
- `src/backtest/evaluate.py:9` günlük aggregate + 0-filled + fallback tpy.
- `dashboard/backend/app.py:890` aynı günlük mantığı (0-filled).
- `config/experiment.yaml:15` ve `PROTOCOL.md:12` **değişmedi**.

## Test
`tests/test_sharpe_annualization.py:1` aynı seriye yanlış vs doğru uygulandığında doğru olanın kullanıldığını kanıtlar:
```
wrong (per-trade+365): 5.83
correct daily+365: 11.39
correct per-trade+tpy (1460): 11.66
PASS
```
`py -3 tests/test_sharpe_annualization.py` → PASS.
`py -3 tests/test_capital_protection.py` → hâlâ PASS.

## Sonuç
- Eski dashboard `6.02` artık raporlanmıyor, yeni code günlük Sharpe döndürüyor (4 günde ~11–14, ama 4 gün örneklem çok kısa).
- Geçmiş `docs/TAM_RAPOR_2026-09-04.md` içindeki 6.02 değeri **not trusted** olarak işaretli.
- PROTOCOL threshold'ları değişmedi.
