# Phase 2 — Walk-Forward (HAZIR, ÇALIŞTIRILMADI)

> **Durum:** Runner hazır, Phase 2 **henüz KOŞULMADI**. Kullanıcı onayı bekleniyor.

## Tek Komut
```bash
py -3 scripts/run_phase02.py              # dry-run iskelet + guard kontrol
py -3 scripts/run_phase02.py --no-dry-run # gerçek backtest (final_test_A guard ile)
# veya
make walkforward  # Makefile walkforward target (eski)
```

## Çıktı Yapısı (runner oluşturur)
```
experiments/phase_02_walkforward/
  README.md
  config_snapshot.yaml      # config/experiment.yaml kopyası
  config_snapshot.json      # config/freqtrade.example.json kopyası
  folds/
    folds.csv               # 9 fold (2020-01-01→2023-06-30, train 365 val 90 test 90 step 90 expanding false)
  trades.csv                # placeholder, --no-dry-run'da freqtrade backtest doldurur
  metrics.csv               # sharpe/sortino/max_dd/pf (günlük 365)
  regime_report.csv         # bull/bear/high_vol kırılımlı
  overlap_report.txt        # gap -455 OVERLAP (foldlar bağımsız değil)
  run_metadata.json         # timestamp, git commit/tag, config hash, data range, universe, fee 0.001, slippage 5bps, python versiyon
```

## Güvenlik — final_test_A
- `config/experiment.yaml:7` `final_test_A: 2023-07-01 → 2023-12-31`
- Runner `generate_folds("2020-01-01","2023-06-30")` kullanır → son test `2023-06-19` → final_A öncesi
- Her fold `test` aralığı final_A ile örtüşürse `GUARD FAIL` → abort (exit 2)
- `expanding:false` **değişmedi** (korunuyor)

## Ön Koşul
- `freqtrade/user_data/data/binance/` OHLCV **NOT READY** — önce `make download` veya `python scripts/download_data.py --pairs BTC/USDT ETH/USDT --timeframe 5m --days 400`
- `verify_dryrun.py 9/9` zaten tamam

## Notlar
- `src/backtest/walk_forward.py:7` `note` alanı filtreleniyor (aksi halde TypeError)
- `src/backtest/evaluate.py:9` günlük Sharpe/daily (eski per-trade+365 fix)
- `PROTOCOL.md` değişmedi
