"""Sanity v2 — corrected MaxDD (wallet) + PF (abs), Sharpe unchanged. Old files NOT overwritten."""
import pathlib, json, zipfile, glob, sys
ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd

m = pd.read_csv(ROOT/"experiments/phase_02_walkforward/metrics.csv")
t = pd.read_csv(ROOT/"experiments/phase_02_walkforward/trades.csv")
t["close_date"] = pd.to_datetime(t["close_date"])

bt_dir = ROOT/"freqtrade/user_data/backtest_results/phase02"
zips = sorted(bt_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime)
ft_by_fold = {}
for zp in zips:
    z = zipfile.ZipFile(zp)
    n = [x for x in z.namelist() if x.endswith(".json") and "config" not in x][0]
    d = json.loads(z.read(n))
    bs = d["strategy"]["BaselineStrategy"]
    bts = bs["backtest_start"][:10]
    ft_by_fold[bts] = bs

rows = []
for _, r in m.sort_values("fold").iterrows():
    fold = int(r["fold"])
    sub = t[t["fold"] == fold].copy()
    # PF abs (correct, matches FT)
    gw = sub[sub["profit_abs"] > 0]["profit_abs"].sum()
    gl = abs(sub[sub["profit_abs"] <= 0]["profit_abs"].sum())
    pf_abs = float(gw/gl) if gl else float("inf")
    # MaxDD wallet simple: 100 + cum daily_abs
    sub["date"] = pd.to_datetime(sub["close_date"]).dt.date
    daily_abs = sub.groupby("date")["profit_abs"].sum()
    full_idx = pd.date_range(r["test_start"], (pd.Timestamp(r["test_end"])-pd.Timedelta(days=1)).date(), freq="D").date
    daily_full = pd.Series(0.0, index=full_idx)
    daily_full.update(daily_abs)
    eq = 100 + daily_full.cumsum()
    dd = float(((eq-eq.cummax())/eq.cummax()).min())
    # FT reference by test_start
    ft = ft_by_fold.get(r["test_start"], {})
    rows.append({
        "fold": fold,
        "test_start": r["test_start"], "test_end": r["test_end"],
        "trade_count": int(r["trade_count"]),
        "net_abs": r["net_abs"],
        "daily_sharpe_our": r["daily_sharpe"],
        "ft_wallet_sharpe": round(ft.get("wallet_stats", {}).get("sharpe", float("nan")), 3) if ft else "",
        "max_dd_old_ratio": r["max_dd"],
        "max_dd_new_wallet": round(dd, 4),
        "ft_max_dd": round(ft.get("max_drawdown_account", float("nan")), 4) if ft else "",
        "pf_old_ratio": r["profit_factor"],
        "pf_new_abs": round(pf_abs, 3),
        "ft_pf": round(ft.get("profit_factor", float("nan")), 3) if ft else "",
    })
    print(f"fold {fold} PF {r['profit_factor']}->{pf_abs:.3f} (FT {ft.get('profit_factor',0):.3f}) DD {r['max_dd']}->{dd:.4f} (FT {ft.get('max_drawdown_account',0):.4f}) Sharpe {r['daily_sharpe']} (FTw {ft.get('wallet_stats',{}).get('sharpe',0):.3f})")

out = ROOT/"experiments/phase_02_walkforward/metrics_v2.csv"
pd.DataFrame(rows).to_csv(out, index=False)
print(f"wrote {out} (old metrics.csv untouched)")
