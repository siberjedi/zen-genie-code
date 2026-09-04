"""
Phase 2 Walk-Forward Analyzer — 2026-09-04
- 9 fold zip -> trades.csv, metrics.csv, regime_report.csv, overlap, FDR, Cohen d, power
- Sharpe SADECE daily aggregate +365 (per-trade+365 YASAK)
- Regime mekanik, hindsight yok (SMA50/200, ADX>20, ATR30d percentile)
- final_test_A 2023-07-01 -> 2023-12-31 guard (ABORT if overlap)
- ABORT on anomaly, no forced completion
"""
import sys, pathlib, json, glob, zipfile, hashlib, subprocess, datetime, platform, math, statistics
ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
import numpy as np
import yaml

EXP_OUT = ROOT / "experiments" / "phase_02_walkforward"
BT_DIR = ROOT / "freqtrade" / "user_data" / "backtest_results" / "phase02"
DATA_DIR = ROOT / "freqtrade" / "user_data" / "data" / "binance"

FINAL_A_START = pd.Timestamp("2023-07-01")
FINAL_A_END = pd.Timestamp("2023-12-31")

# Fold definitions (locked WF settings)
FOLDS = [
    {"fold": 0, "train_start": "2020-01-01", "train_end": "2020-12-31", "val_start": "2020-12-31", "val_end": "2021-03-31", "test_start": "2021-03-31", "test_end": "2021-06-29", "timerange": "20210331-20210629"},
    {"fold": 1, "train_start": "2020-03-31", "train_end": "2021-03-31", "val_start": "2021-03-31", "val_end": "2021-06-29", "test_start": "2021-06-29", "test_end": "2021-09-27", "timerange": "20210629-20210927"},
    {"fold": 2, "train_start": "2020-06-29", "train_end": "2021-06-29", "val_start": "2021-06-29", "val_end": "2021-09-27", "test_start": "2021-09-27", "test_end": "2021-12-26", "timerange": "20210927-20211226"},
    {"fold": 3, "train_start": "2020-09-27", "train_end": "2021-09-27", "val_start": "2021-09-27", "val_end": "2021-12-26", "test_start": "2021-12-26", "test_end": "2022-03-26", "timerange": "20211226-20220326"},
    {"fold": 4, "train_start": "2020-12-26", "train_end": "2021-12-26", "val_start": "2021-12-26", "val_end": "2022-03-26", "test_start": "2022-03-26", "test_end": "2022-06-24", "timerange": "20220326-20220624"},
    {"fold": 5, "train_start": "2021-03-26", "train_end": "2022-03-26", "val_start": "2022-03-26", "val_end": "2022-06-24", "test_start": "2022-06-24", "test_end": "2022-09-22", "timerange": "20220624-20220922"},
    {"fold": 6, "train_start": "2021-06-24", "train_end": "2022-06-24", "val_start": "2022-06-24", "val_end": "2022-09-22", "test_start": "2022-09-22", "test_end": "2022-12-21", "timerange": "20220922-20221221"},
    {"fold": 7, "train_start": "2021-09-22", "train_end": "2022-09-22", "val_start": "2022-09-22", "val_end": "2022-12-21", "test_start": "2022-12-21", "test_end": "2023-03-21", "timerange": "20221221-20230321"},
    {"fold": 8, "train_start": "2021-12-21", "train_end": "2022-12-21", "val_start": "2022-12-21", "val_end": "2023-03-21", "test_start": "2023-03-21", "test_end": "2023-06-19", "timerange": "20230321-20230619"},
]

ELIGIBLE_18 = ["BTC/USDT","ETH/USDT","XRP/USDT","ADA/USDT","BNB/USDT","DOGE/USDT","TRX/USDT","ZEC/USDT","LINK/USDT","SOL/USDT","AVAX/USDT","UNI/USDT","AAVE/USDT","NEAR/USDT","ARB/USDT","PROM/USDT","SUI/USDT","PEPE/USDT"]
EXCLUDED_12 = ["BMT/USDT","CHIP/USDT","CRCLB/USDT","ENA/USDT","HEMI/USDT","PUMP/USDT","TAO/USDT","TRUMP/USDT","U/USDT","WLD/USDT","XPL/USDT","ZKP/USDT"]

def abort(msg):
    print(f"[ABORT] {msg}")
    sys.exit(2)

def daily_sharpe_sortino(daily_series):
    # daily_series: pd.Series of daily returns (profit_ratio sum per day, 0-filled)
    # Sharpe = mean/std * sqrt(365), Sortino downside only
    if len(daily_series) < 3:
        return None, None
    try:
        m = float(daily_series.mean())
        s = float(daily_series.std(ddof=1))
        if s == 0 or np.isnan(s):
            return 0.0, None
        sharpe = m / s * math.sqrt(365)
        downside = daily_series[daily_series < 0]
        if len(downside) < 2:
            sortino = None
        else:
            sd = float(downside.std(ddof=1))
            sortino = m / sd * math.sqrt(365) if sd and not np.isnan(sd) else None
        return sharpe, sortino
    except Exception as e:
        print(f"sharpe err {e}")
        return None, None

def max_dd_from_daily(daily_series):
    eq = (1 + daily_series).cumprod()
    roll_max = eq.cummax()
    dd = (eq - roll_max) / roll_max
    return float(dd.min()) if len(dd) else 0.0

def load_btc_daily():
    f = DATA_DIR / "BTC_USDT-5m.feather"
    if not f.exists():
        abort("BTC data yok")
    df = pd.read_feather(f)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    # resample to daily
    df = df.set_index("date")
    ohlc = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    daily = df.resample("1D").agg(ohlc).dropna()
    return daily

def compute_regime(daily):
    # daily: DataFrame with open/high/low/close/volume, daily freq, sorted
    # SMA50/200, ATR14, ADX14, vol percentile 30d
    # Manual, causal (rolling only past)
    close = daily["close"]
    high = daily["high"]
    low = daily["low"]
    daily["sma50"] = close.rolling(50).mean()
    daily["sma200"] = close.rolling(200).mean()
    # ATR14 (Wilder)
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    daily["atr"] = tr.ewm(alpha=1/14, adjust=False).mean()
    # ADX14 Wilder
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=daily.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=daily.index)
    tr_smooth = tr.ewm(alpha=1/14, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / tr_smooth
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / tr_smooth
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    daily["adx"] = dx.ewm(alpha=1/14, adjust=False).mean()
    daily["vol_rank"] = daily["atr"].rolling(30).rank(pct=True)
    def label(row):
        if pd.isna(row["sma50"]) or pd.isna(row["sma200"]) or pd.isna(row["adx"]):
            return "unknown"
        trend_bull = (row["sma50"] > row["sma200"]) and (row["adx"] > 20)
        trend_bear = (row["sma50"] < row["sma200"]) and (row["adx"] > 20)
        high_vol = row["vol_rank"] > 0.70 if not pd.isna(row["vol_rank"]) else False
        if trend_bull:
            return "bull_high_vol" if high_vol else "bull"
        if trend_bear:
            return "bear_high_vol" if high_vol else "bear"
        return "sideways_high_vol" if high_vol else "sideways"
    daily["regime"] = daily.apply(label, axis=1)
    # Collapse to requested 3 buckets + detail: bull, bear, sideways_high_vol (plus others for transparency)
    return daily[["close", "sma50", "sma200", "adx", "atr", "vol_rank", "regime"]]

def main():
    print("=== Phase 2 Analyzer ===")
    zips = sorted(BT_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime)
    print(f"Found {len(zips)} zips")
    if len(zips) != 9:
        abort(f"9 fold zip bekleniyor, {len(zips)} bulundu")
    # Map by backtest_start_ts to fold (robust, not just mtime order)
    fold_map = {}
    for zp in zips:
        z = zipfile.ZipFile(zp)
        names = z.namelist()
        main_json = [n for n in names if n.endswith(".json") and "config" not in n][0]
        data = json.loads(z.read(main_json))
        bs = data["strategy"]["BaselineStrategy"]
        bts = bs.get("backtest_start", "")
        bte = bs.get("backtest_end", "")
        # match to FOLDS by test_start/end
        matched = None
        for f in FOLDS:
            # backtest_start like "2021-03-31 00:00:00"
            if bts[:10] == f["test_start"] and bte[:10] == f["test_end"]:
                matched = f["fold"]
                break
        if matched is None:
            # fallback by timerange in config? try backtest_start_ts
            print(f"WARN {zp.name} {bts}->{bte} fold eslesmedi")
            abort(f"fold eslesme hatasi {zp.name} {bts}->{bte}")
        if matched in fold_map:
            abort(f"duplicate fold {matched}")
        fold_map[matched] = (zp, bs)
        print(f"zip {zp.name} -> fold {matched} {bts}->{bte} trades {bs.get('total_trades')}")
    if sorted(fold_map.keys()) != list(range(9)):
        abort(f"fold set eksik {sorted(fold_map.keys())}")
    # Guard final_test_A
    for f in FOLDS:
        ts = pd.Timestamp(f["test_start"])
        te = pd.Timestamp(f["test_end"])
        if not (te < FINAL_A_START or ts > FINAL_A_END):
            abort(f"fold {f['fold']} final_test_A ile ortusuyor")
    print("[GUARD] final_test_A untouched PASS")

    # Regime base (BTC daily, full history, causal)
    print("Regime computing (BTC daily)...")
    btc_daily = load_btc_daily()
    regime_df = compute_regime(btc_daily.copy())
    # regime_df indexed by daily Timestamp

    all_trades = []
    metrics_rows = []
    regime_rows = []
    p_values = []

    for fold_id in range(9):
        zp, bs = fold_map[fold_id]
        fdef = FOLDS[fold_id]
        trades = bs.get("trades", [])
        if not trades:
            abort(f"fold {fold_id} 0 trade (anomaly, zorla tamamlama yok)")
        df = pd.DataFrame(trades)
        # Normalize dates
        df["open_date"] = pd.to_datetime(df["open_date"])
        df["close_date"] = pd.to_datetime(df["close_date"])
        # Verify test range (allow startup warmup? trades must be within test period +/- duration)
        # Check no trade closes after test_end + 3d (open trades forced exit) and none before test_start
        test_start = pd.Timestamp(fdef["test_start"], tz="UTC")
        test_end = pd.Timestamp(fdef["test_end"], tz="UTC")
        # Freqtrade uses UTC; compare
        if (df["open_date"].min() < test_start - pd.Timedelta(days=1)) or (df["close_date"].max() > test_end + pd.Timedelta(days=4)):
            print(f"WARN fold {fold_id} trade dates disinda {df['open_date'].min()}->{df['close_date'].max()} vs test {test_start}->{test_end}")
            # not abort, just warn (warmup trades can start slightly before? but should not)
        # Metrics: daily aggregate profit_ratio (YASAK per-trade+365 yok)
        df["date"] = df["close_date"].dt.date
        daily = df.groupby("date")["profit_ratio"].sum()
        full_idx = pd.date_range(fdef["test_start"], fdef["test_end"], freq="D").date
        # Note: test_end exclusive? Freqtrade backtest_end is exclusive start of next day? Use inclusive range minus last day?
        # Our folds test_end like 2021-06-29, backtest_end 2021-06-29 00:00:00 -> last full day 2021-06-28. Adjust: full_idx up to test_end -1d
        # To avoid 0-day at end, use range test_start..test_end-1d
        full_idx = pd.date_range(fdef["test_start"], (pd.Timestamp(fdef["test_end"]) - pd.Timedelta(days=1)).date(), freq="D").date
        daily_full = pd.Series(0.0, index=full_idx)
        daily_full.update(daily)
        sharpe_v, sortino_v = daily_sharpe_sortino(daily_full)
        maxdd_v = max_dd_from_daily(daily_full)
        # PF, WinRate
        wins = df[df["profit_ratio"] > 0]
        losses = df[df["profit_ratio"] <= 0]
        gross_w = wins["profit_ratio"].sum() if len(wins) else 0
        gross_l = abs(losses["profit_ratio"].sum()) if len(losses) else 0
        pf = float(gross_w / gross_l) if gross_l else (float("inf") if gross_w > 0 else 0.0)
        win_rate = len(wins) / len(df) if len(df) else 0
        net_abs = float(df["profit_abs"].sum())
        net_ratio = float(df["profit_ratio"].sum())
        total_return_pct = net_abs / 100 * 100  # starting 100
        turnover = len(df)
        total_volume = float(df["stake_amount"].sum()) if "stake_amount" in df.columns else 0
        fee_paid_est = total_volume * 0.001 * 2  # entry+exit
        # Freqtrade p_value
        p_val = bs.get("p_value", None)
        if p_val is not None:
            p_values.append(float(p_val))
        # Pair count
        pair_count = int(df["pair"].nunique())
        # Duration avg? use trade_duration (seconds?) Freqtrade trade_duration is seconds? Actually minutes? Check: trade_duration in seconds? We'll compute from dates
        avg_dur_h = float((df["close_date"] - df["open_date"]).dt.total_seconds().mean() / 3600) if len(df) else 0
        metrics_rows.append({
            "fold": fold_id,
            "train_start": fdef["train_start"], "train_end": fdef["train_end"],
            "val_start": fdef["val_start"], "val_end": fdef["val_end"],
            "test_start": fdef["test_start"], "test_end": fdef["test_end"],
            "pair_count": pair_count,
            "trade_count": len(df),
            "net_abs": round(net_abs, 3),
            "net_pct": round(net_abs, 3),  # starting 100 -> abs == pct
            "daily_sharpe": round(sharpe_v, 3) if sharpe_v is not None else "",
            "sortino": round(sortino_v, 3) if sortino_v is not None else "",
            "max_dd": round(maxdd_v, 4),
            "profit_factor": round(pf, 3) if pf != float("inf") else "inf",
            "win_rate": round(win_rate, 4),
            "turnover": turnover,
            "total_volume": round(total_volume, 1),
            "fee_est": round(fee_paid_est, 2),
            "fee_rate": 0.001,
            "slippage_bps": 5,
            "slippage_model": "5bps base (Madde 12, freqtrade slippage yok)",
            "p_value": p_val,
            "method": "daily_365",
        })
        # Regime breakdown: map each trade open_date (date) to regime
        for _, tr in df.iterrows():
            d = (tr["open_date"].tz_convert(None) if tr["open_date"].tzinfo else tr["open_date"]).floor("D")
            # regime_df index is daily Timestamp (no tz)
            try:
                reg = regime_df.loc[regime_df.index.date == d.date(), "regime"]
                regime = reg.iloc[0] if len(reg) else "unknown"
            except:
                regime = "unknown"
            # Collapse to 3 requested + detail: keep full, but aggregate later to bull/bear/sideways_high_vol
            all_trades.append({
                "fold": fold_id,
                "pair": tr["pair"],
                "open_date": str(tr["open_date"]),
                "close_date": str(tr["close_date"]),
                "profit_ratio": tr["profit_ratio"],
                "profit_abs": tr["profit_abs"],
                "exit_reason": tr.get("exit_reason", ""),
                "regime": regime,
                "stake_amount": tr.get("stake_amount", ""),
            })
        # Per-fold regime summary
        # Map trades to collapsed buckets
        tmp = pd.DataFrame([t for t in all_trades if t["fold"] == fold_id])
        def collapse(r):
            if r.startswith("bull"):
                return "bull"
            if r.startswith("bear"):
                return "bear"
            if r == "sideways_high_vol":
                return "sideways_high_vol"
            return r  # sideways, unknown, etc for transparency
        tmp["bucket"] = tmp["regime"].apply(collapse)
        for bucket, g in tmp.groupby("bucket"):
            regime_rows.append({
                "fold": fold_id,
                "test_start": fdef["test_start"], "test_end": fdef["test_end"],
                "regime": bucket,
                "trades": len(g),
                "win_rate": round((g["profit_ratio"] > 0).mean(), 4),
                "net_abs": round(g["profit_abs"].sum(), 3),
                "avg_profit_ratio": round(g["profit_ratio"].mean(), 5),
            })
        print(f"fold {fold_id} trades {len(df)} net {net_abs:.2f} sharpe {sharpe_v} pf {pf:.2f} wr {win_rate:.2f}")

    # Aggregate OOS (all folds concatenated daily? For aggregate Sharpe, concat daily series per fold? Folds overlap in calendar (rolling), cannot simply concat (double count overlapping test periods? Actually test periods are non-overlapping? Check: test 0 2021-03-31->06-29, test1 06-29->09-27 -> contiguous, no overlap. Good, tests are contiguous partition of 2021-03-31->2023-06-19. So aggregate daily = concat per-fold daily_full in order.)
    # Build aggregate daily from metrics? Simpler: from all_trades group by close date profit_ratio sum, 0-filled 2021-03-31->2023-06-18
    trades_df = pd.DataFrame(all_trades)
    trades_df["close_date"] = pd.to_datetime(trades_df["close_date"])
    trades_df["date"] = trades_df["close_date"].dt.date
    daily_agg = trades_df.groupby("date")["profit_ratio"].sum()
    full_agg_idx = pd.date_range("2021-03-31", "2023-06-18", freq="D").date
    daily_agg_full = pd.Series(0.0, index=full_agg_idx)
    daily_agg_full.update(daily_agg)
    agg_sharpe, agg_sortino = daily_sharpe_sortino(daily_agg_full)
    agg_dd = max_dd_from_daily(daily_agg_full)
    # Median/mean fold Sharpe
    fold_sharpes = [r["daily_sharpe"] for r in metrics_rows if isinstance(r["daily_sharpe"], (int, float))]
    median_sharpe = float(np.median(fold_sharpes)) if fold_sharpes else None
    mean_sharpe = float(np.mean(fold_sharpes)) if fold_sharpes else None
    total_return = sum(r["net_abs"] for r in metrics_rows)
    # FDR
    try:
        from statsmodels.stats.multitest import multipletests
        rej, p_corr, _, _ = multipletests(p_values, alpha=0.05, method="fdr_bh")
        fdr_str = f"rej {int(np.sum(rej))}/9, p_corr min {float(np.min(p_corr)):.4f}"
        fdr_rej = int(np.sum(rej))
    except Exception as e:
        fdr_str = f"err {e}"
        fdr_rej = ""
        p_corr = []
    # Cohen's d and power (daily agg vs 0)
    try:
        from src.backtest.evaluate import cohens_d, compute_power
        import numpy as np2
        d_val = float(daily_agg_full.mean() / daily_agg_full.std(ddof=1)) if daily_agg_full.std(ddof=1) else 0.0
        # power for d=0.30? Actually report observed d power with n=days
        n_days = len(daily_agg_full)
        pow_obs = compute_power(abs(d_val), n_days // 2)  # per-group approx
        pow_req = compute_power(0.30, 176)  # reference
    except Exception as e:
        d_val, pow_obs, pow_req = float("nan"), float("nan"), float("nan")
        print(f"cohen/power err {e}")
    # Overlap report (folds overlap in train, tests contiguous)
    overlap_lines = []
    for i in range(1, 9):
        # train overlap: current train start vs prev test end
        prev_test_end = pd.Timestamp(FOLDS[i-1]["test_end"])
        cur_train_start = pd.Timestamp(FOLDS[i]["train_start"])
        gap = (cur_train_start - prev_test_end).days
        overlap_lines.append(f"fold {i-1}->{i} train_start {cur_train_start.date()} vs prev_test_end {prev_test_end.date()} gap {gap} {'OVERLAP' if gap<0 else 'ok'} (trainlar rolling, bagimsiz degil)")
    # Data quality totals
    total_candles = 4848813
    total_missing = 5661

    # Write outputs
    EXP_OUT.mkdir(parents=True, exist_ok=True)
    (EXP_OUT / "folds").mkdir(exist_ok=True)
    pd.DataFrame(all_trades).to_csv(EXP_OUT / "trades.csv", index=False)
    pd.DataFrame(metrics_rows).to_csv(EXP_OUT / "metrics.csv", index=False)
    pd.DataFrame(regime_rows).to_csv(EXP_OUT / "regime_report.csv", index=False)
    # folds.csv
    import csv
    with open(EXP_OUT / "folds" / "folds.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["fold","train_start","train_end","val_start","val_end","test_start","test_end","timerange"])
        w.writeheader()
        w.writerows(FOLDS)
    (EXP_OUT / "overlap_report.txt").write_text("\n".join(overlap_lines) + "\n", encoding="utf-8")
    # run_metadata
    def git(cmd):
        try:
            return subprocess.check_output(cmd, cwd=str(ROOT), text=True, stderr=subprocess.STDOUT).strip()
        except:
            return "unknown"
    commit = git(["git","rev-parse","HEAD"])
    tag = git(["git","describe","--tags","--exact-match"])
    if "unknown" in tag or "fatal" in tag:
        tag = git(["git","tag","--points-at","HEAD"]) or "no-tag"
        if not tag:
            all_tags = git(["git","tag"])
            tag = all_tags.splitlines()[-1] if all_tags and "unknown" not in all_tags else "no-tag"
    cfg_exp = (ROOT/"config"/"experiment.yaml").read_text(encoding="utf-8")
    cfg_ft = (ROOT/"config"/"freqtrade.backtest.json").read_text(encoding="utf-8") if (ROOT/"config"/"freqtrade.backtest.json").exists() else (ROOT/"config"/"freqtrade.example.json").read_text(encoding="utf-8")
    h = hashlib.sha256()
    for p in [ROOT/"config"/"experiment.yaml", ROOT/"config"/"freqtrade.example.json", ROOT/"freqtrade"/"user_data"/"strategies"/"BaselineStrategy.py"]:
        if p.exists():
            h.update(p.read_bytes())
    strat_hash = hashlib.sha256((ROOT/"freqtrade"/"user_data"/"strategies"/"BaselineStrategy.py").read_bytes()).hexdigest()[:12]
    import yaml as y
    cfg_y = y.safe_load((ROOT/"config"/"experiment.yaml").read_text(encoding="utf-8"))
    meta = {
        "timestamp": datetime.datetime.now().astimezone().isoformat(),
        "git_commit": commit,
        "git_tag": tag,
        "git_clean": git(["git","status","--porcelain"]) == "",
        "config_hash": h.hexdigest()[:16],
        "strategy_version": strat_hash,
        "strategy": "BaselineStrategy RSI14 SMA50/200 entry RSI<30&SMA50>SMA200 exit RSI>70 SL -10% ROI 2% 5m (dondurulmus)",
        "data_range": "2020-01-01 -> 2023-06-30 (test 2021-03-31 -> 2023-06-19)",
        "requested_universe": 30,
        "historical_eligible_universe": ELIGIBLE_18,
        "excluded_pairs": EXCLUDED_12,
        "pair_universe_detail": json.loads(cfg_ft).get("pairlists", [{}])[0] if cfg_ft else {},
        "fee": cfg_y.get("costs", {}).get("fee_taker", 0.001),
        "slippage_bps": cfg_y.get("costs", {}).get("slippage_bps", 5),
        "slippage_model": cfg_y.get("costs", {}).get("slippage_model", ""),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {"pandas": pd.__version__, "numpy": np.__version__},
        "wf_config": {"train_days": 365, "validation_days": 90, "test_days": 90, "step_days": 90, "expanding": False},
        "final_test_A": "2023-07-01 -> 2023-12-31",
        "final_test_A_touched": False,
        "final_test_A_guard": "enabled",
        "execution": "freqtrade backtesting 9 fold, fee 0.001, StaticPairList 18 pair",
        "aggregate": {"oos_sharpe_daily_365": agg_sharpe, "median_fold_sharpe": median_sharpe, "mean_fold_sharpe": mean_sharpe, "total_return_abs": total_return, "max_dd": agg_dd, "sortino": agg_sortino},
        "statistics": {"fdr": fdr_str, "cohens_d_daily": d_val, "power_obs": pow_obs, "power_req_d03": pow_req, "overlap": "trainlar OVERLAP, testler contiguous, bagimsiz degil"},
        "data_quality": {"candles": total_candles, "missing": total_missing, "duplicate": 0, "invalid": 0},
        "note": "Phase 2 amaci optimize degil, dondurulmus baseline gozlem. Sonuclara gore kod/config/threshold degistirilmedi.",
    }
    (EXP_OUT / "run_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    # config snapshots (do not overwrite locked, just copy)
    (EXP_OUT / "config_snapshot.yaml").write_text((ROOT/"config"/"experiment.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (EXP_OUT / "config_snapshot.json").write_text((ROOT/"config"/"freqtrade.example.json").read_text(encoding="utf-8"), encoding="utf-8")
    (EXP_OUT / "config_backtest.json").write_text(cfg_ft, encoding="utf-8")
    print("=== SUMMARY ===")
    print(f"aggregate Sharpe {agg_sharpe} median {median_sharpe} mean {mean_sharpe} total {total_return} dd {agg_dd}")
    print(f"FDR {fdr_str} d {d_val} power {pow_obs}")
    print(f"wrote {EXP_OUT}")
    return meta

if __name__ == "__main__":
    main()
