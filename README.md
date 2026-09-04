# Zen-Genie — AI Trader (araştırma çekirdeği)

Bu repo strateji/araştırma çekirdeğidir: `src/` (backtest, metrik, risk, RL, rejim, sinyal),
`scripts/` (veri indirme, analiz, doğrulama), `docs/` (protokol + raporlar).

> Not: tam canlı yığın (`dashboard/`, `config/`, `experiments/`, `Makefile`) bu pakette
> bilerek yoktur. Aşağıdaki kurulum araştırma kodunu çalıştırır.

## Kurulum
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
- `TA-Lib` sistem kütüphanesi ister (Windows'ta önceden derlenmiş tekerlek/conda önerilir).
- `playwright` kullanacaksan ayrıca: `playwright install` (tarayıcı indirir).

## Kullanım (örnekler)
```bat
.venv\Scripts\activate
python scripts/download_data.py --pairs BTC/USDT --timeframe 5m --days 30
python scripts/verify_dryrun.py
```
Detay: `PROTOCOL.md`, `docs/TAM_RAPOR_2026-09-04.md`.
Canlı/paper trade YOKTUR — bu paket yalnızca araştırma kodudur.
