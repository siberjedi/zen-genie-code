# Faz 1 — LOCK (2026-08-27)

**Durum:** RUNNING — `ai-trader-dryrun` container `freqtradeorg/freqtrade:stable` ile live dry-run'da.
**Başlangıç:** `experiments/phase_01_dryrun/STARTED_AT:1`
**Config:** `config/freqtrade.example.json:1` (dry_run=true, wallet=10, BTC/USDT ETH/USDT, BaselineStrategy)
**DB:** `freqtrade/user_data/tradesv3.dryrun.sqlite` (bind mount, canlı yazıyor)
**Doğrulama:** `py -3 scripts/verify_dryrun.py` → 8/9 (tek fail: 7 gün henüz dolmadı — beklenen)

## Kural (kullanıcı onayı ile)
> **Faz 1 7 gün tamamlanmadan Faz 2/3/4 koduna dokunulmaz.**

Gerekçe: "20 klasör hazır, bot kapalı" anti-pattern'ini engellemek. Faz 2 walk-forward, Faz 3 FreqAI iskeleti mevcut ama donduruldu.

## 7 Gün İçin İzlenecek
- `docker logs -f ai-trader-dryrun` — heartbeat RUNNING
- `docker exec ai-trader-dryrun sqlite3 /freqtrade/user_data/tradesv3.dryrun.sqlite "SELECT count(*) FROM trades;"` — trade sayısı
- `py -3 scripts/verify_dryrun.py` — daily check
- Slippage/fee gerçekliği Faz 10'da karşılaştırılacak (şimdi sadece loglanıyor)

## Faz 1 Çıkış Kriteri (PROTOCOL.md)
- Canlı veri OK, emir simülasyonu OK, bakiye/P&L/komisyon OK, geçmiş kayıtlı, 7 gün kesintisiz → sonra Faz 2'ye geç.
