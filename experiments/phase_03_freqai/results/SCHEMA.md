# Faz 3 — Sonuç Şeması (deney henüz KOŞULMADI; dosya yok)

Deney çalıştığında `results/` altına yazılacaklar (şimdilik yalnızca şema):

- `results/val_trades_<seed>.csv` — kolonlar: `fold, pair, open_date, close_date,
  profit_ratio, profit_abs, exit_reason, stake_amount` (Phase 2 `trades.csv` ile aynı şema).
- `results/val_metrics.csv` — satır başına (fold, seed): `fold, seed, n_train, n_val,
  trade_count, net_abs, daily_sharpe, sortino, max_dd_wallet, profit_factor_abs,
  win_rate, turnover, total_volume, fee_est, method=daily_365`.
- `results/seed_summary.csv` — satır başına seed: `seed, mean_val_sharpe, std_val_sharpe,
  delta_vs_baseline, wf_win_rate_vs_baseline`.
- `results/comparison.json` — `delta`, `check_thresholds()` çıktısı, FDR/d/power, effect size + CI.

Birincil karşılaştırma: FreqAI validation Sharpe − Baseline validation Sharpe
(aynı pencere/universe/maliyet). İkincil bağlam: Faz 2 aggregate −1.807.
