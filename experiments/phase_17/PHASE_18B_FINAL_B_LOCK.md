# PHASE 18B RESULT — FINAL_B DOWNLOAD → LOCK

**Statü:** LOCKED. Backtest/strateji/feature/tuning/perf YOK. No-peek korundu.

## Source
- Konvansiyon: Binance REST `/api/v3/klines` (BTCUSDT, 5m, limit=1000, rate-limit
  0.12s) — **Phase 500 (P5 holdout) ile birebir aynı kaynak ve şema**.
  Yeni/alternatif provider kullanılmadı.
- URL: `https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&startTime=1704067200000&endTime=1719791999999&limit=1000`
- Pencere: 2024-01-01 00:00 UTC (inclusive) → 2024-07-01 00:00 UTC (exclusive) =
  FINAL_B (2024H1, 2024-06-30 23:55 UTC'ye kadar).

## Artifact
- Path: `experiments/phase_17/holdout/BTC_USDT-5m_2024H1.feather`
- Şema: `date, open, high, low, close, volume` (date = open_time, UTC) — P5 ile aynı.

## Date range
- first: `2024-01-01 00:00:00+00:00` · last: `2024-06-30 23:55:00+00:00`

## Rows
- **52.416 / 52.416** (182 gün × 288 bar) — dolu pencere, eksik yok.

## File size
- **1.709.898 B**

## SHA256
- **`28f88258b976ee88382b3e176f8ce8db9f4827bc703c71f93c7d18235d0b9387`**
- İki kez bağımsız hesaplandı: `hash_1 == hash_2` → **MATCH**.

## Manifest
- `experiments/phase_17/holdout/PHASE_18B_FINAL_B_MANIFEST.json`
- İçerik: experiment_id, holdout_id, source_url, local_path, date_start/end,
  timeframe, symbol, window_ms, row_count, expected_rows, file_size_bytes,
  sha256, sha256_recheck, downloaded_at, file_mtime, validation_status,
  duplicates/nulls/monotonic/out_of_window/missing_intervals/bad_ohlc,
  date_first/last, schema, integrity_pass.

## Validation
- duplicates = 0 · nulls = 0 · monotonic = True · out_of_window = 0 ·
  missing_intervals = 0 · OHLC relationship violations = 0 ·
  nonpositive bars = 0 · **integrity_pass = True**
- Yalnızca DATA QUALITY kontrolü; hiçbir alpha/return/Sharpe metriği
  hesaplanmadı (no-peek).

## Lock
- Artifact immutable kabul edildi: manifest + sha256 pin + registry kaydı.
- Guard mekanizması: pin, manifest'teki hash ile her okumada karşılaştırılır;
  değişiklik/değiştirme/yeniden-indirme → pin uyuşmazlığı yakalar.
  Production koduna dokunulmadı (p5_splits değişmedi — mevcut konvansiyon
  metadata katmanında kilitli).

## Registry
- `HOLDOUT_REGISTRY.md` FINAL_B bölümüne append-only lock satırı eklendi
  (önceki assignment kaydı değiştirilmedi/silinmedi).

## FINAL_A
- CONSUMED — değişmedi.

## FINAL_B
- **ASSIGNED = YES · AVAILABLE = YES · PINNED = YES · CONSUMED = NO · EVALUATED = NO**

## FINAL_C
- **UNTOUCHED** (indirilmedi, erişilmedi).

## Backtest
- **0** · Performance evaluation: **0** · Strategy execution: **0**

## Tests
- `py -m pytest tests/test_holdout_registry.py -q` → 5/5 PASS (beklenen)
- `py -m pytest tests/test_decision_log.py -q` → 6/6 PASS (beklenen)

**COMMIT: NONE · PUSH: NONE**

**VERDICT: READY FOR PHASE 18C**