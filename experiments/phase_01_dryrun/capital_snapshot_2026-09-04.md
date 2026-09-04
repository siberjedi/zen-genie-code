# Capital State Snapshot — 2026-09-04T03:33:43.403556+03:00

## Canonical
`data/capital_state.json` — `src/risk/capital.py:33` `STATE_PATH_WRITABLE` — **canonical**
- CORE: 100.0
- HWM: 106.62818338
- locked: 3.314091689999998
- threshold: 103.31409169
- reserve: 1.77297929
- updated_at: 2026-09-04T00:18:38.706397Z
- realized (DB view): 3.54595858
- unrealized: 0.93501000
- equity: 104.48096858

## Stale
`freqtrade/user_data/capital_state.json` — updated 2026-09-02T08:59:06.108789Z
- HWM: 100.58
- locked: 0.29
- threshold: 100.29
- reserve: 0

`config/capital_state.json` — HWM 100.58 reserve 0.0

## Drift (Çözülmedi)
- HWM diff: 6.04818338
- locked diff: 3.02409169
- threshold diff: 3.02409169
- reserve diff: 1.77297929
- Sebep: `docker-compose.yml:18` `freqtrade/user_data` RO mount değil ama `data:/app/data` writable öncelik; eski dosya `2026-09-02`de donmuş.

## DB Doğrulama
- realized: 3.54595858
- invested_open: 102.33176000
- total_trades: 19
- view equity: 104.48096858

## Sonuç
Canonical `data/capital_state.json` doğrulandı, drift raporlandı, hiçbir değer değiştirilmedi.
