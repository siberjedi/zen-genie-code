# Zen-Genie Dashboard — Faz 1 Dry-Run Terminal

Local-only gözlem paneli. **LIVE TRADING DISABLED** — gerçek emir göndermez.

## URL
- Dashboard: http://127.0.0.1:5173
- API: http://127.0.0.1:8001/docs (FastAPI Swagger)

## Hızlı Başlat
```bash
docker compose up -d --build  # freqtrade + dashboard-api + dashboard
docker ps  # 3 container Up olmalı
```
Sadece dashboard:
```bash
docker compose up -d dashboard-api dashboard
```

Local dev (docker olmadan):
```bash
py -3 -m uvicorn dashboard.backend.app:app --host 127.0.0.1 --port 8001
npm install --prefix dashboard/frontend
npm run dev --prefix dashboard/frontend  # vite 5173 + vite proxy /api -> 8001
```

## Ne nereden geliyor?
| Panel | Kaynak |
|---|---|
| Bot Status / Heartbeat | `docker inspect ai-trader-dryrun` (fallback: DB mtime + STARTED_AT) |
| Portfolio / Trades / Performance | `freqtrade/user_data/tradesv3.dryrun.sqlite` (read-only mode=ro) + `config/freqtrade.example.json` (dry_run_wallet) |
| Live price / klines | Binance public REST `api.binance.com/api/v3/*` (key yok) |
| Experiment (7 gün) | `experiments/phase_01_dryrun/STARTED_AT` + `PHASE_LOCK.md` + `py -3 scripts/verify_dryrun.py` |
| Health (disk/mem/cpu) | `psutil` (host) |
| Logs | `docker logs ai-trader-dryrun` → fallback `freqtrade/user_data/logs/*.log` |
| Controls | `docker compose {stop,start,restart} freqtrade` — sadece dry-run |

## Güvenlik
- Config'ten sadece safe alanlar expose edilir (`safe_config()`): `dry_run`, `pair_whitelist`, `stake_currency` vb. API key/secret asla dönülmez, `live_trading:"DISABLED"` sabit.
- Frontend hiçbir secret saklamaz, localStorage'a key yazılmaz.
- Dashboard portları `127.0.0.1:5173` ve `127.0.0.1:8001` — sadece localhost, dış ağa kapalı. Nginx `location /api/ proxy_pass dashboard-api:8001`.
- Withdraw endpoint yok, `freqtrade.live.json` varsa control 403.
- SQLite `mode=ro`, volume `:ro`. DB şeması değişmez.
- Faz 1 lock dosyalarına yazma yok — sadece okur.

## Dosyalar
- `dashboard/backend/app.py:1` — FastAPI, 12 endpoint, hiçbir trade yazmaz
- `dashboard/backend/Dockerfile:1`
- `dashboard/frontend/src/App.tsx:1` — tek ekran, 12 panel, Recharts, 4-8 sn polling
- `dashboard/frontend/nginx.conf:1` — /api proxy
- `docker-compose.yml:1` — 3 servis + zennet network

## Değişmeyenler (Faz 1 kilidi)
- `freqtrade/user_data/tradesv3.dryrun.sqlite` şeması
- `config/freqtrade.example.json` (dry-run)
- `freqtrade/user_data/strategies/BaselineStrategy.py`
- `scripts/verify_dryrun.py` mantığı
- `experiments/phase_01_dryrun/PHASE_LOCK.md` → LOCKED
