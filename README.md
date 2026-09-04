# Zen-Genie — AI Trader

Nihai protokol: `PROTOCOL.md:1` (locked 2026-08-27). Tek referans.

## Hızlı Başlangıç — Faz 1 Dry-Run
```bash
docker compose up -d --build   # freqtrade + dashboard
# Dashboard: http://127.0.0.1:5173  API: http://127.0.0.1:8001/docs
```
Çıkış kriteri: 7 gün kesintisiz, P&L/komisyon/bakiye doğru (`PROTOCOL.md:1` Faz 1).

## Dashboard (Faz 1 gözlem — local only)
```bash
docker compose up -d dashboard-api dashboard
# veya local dev:
py -3 -m uvicorn dashboard.backend.app:app --host 127.0.0.1 --port 8001
npm install --prefix dashboard/frontend && npm run dev --prefix dashboard/frontend
```
Detay: `dashboard/README.md:1` — LIVE TRADING DISABLED, sadece `tradesv3.dryrun.sqlite` + Binance public REST.

## Fazlar
0 protokol kilidi → `config/experiment.yaml:1` (X/Y eşiklerini sonuçtan önce doldur)
1 dry-run → 2 walk-forward → 3 FreqAI → 4 RL → 5 karşılaştırma → 6-7 X haber → 8 multi-source → 10 paper → 11 real

Anayasa 20 madde: `PROTOCOL.md:1` en alt.

## Doğrulama
```bash
py -3 scripts/verify_dryrun.py  # 8/9 → 7 gün sonra 9/9
docker ps  # ai-trader-dryrun Up, zen-dashboard Up, zen-dashboard-api Up
```
