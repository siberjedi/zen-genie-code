"""Phase 4.15 — RL POLICY/MARKET DIRECTION/MEMORIZATION DIAGNOSTIC (READ-ONLY).

Training YOK, tuning YOK, yeni reward YOK, Final B YOK, veri indirme YOK.

Girdi (salt-okunur):
- tuning47/art_E1_seed{42,7,123,2026,999}.json  (actions/equities/rewards)
- tuning47/run_E1_*.json  (kayıtlı metrikler, doğrulama)
- freqtrade/user_data/data/binance/BTC_USDT-5m.feather (OHLC)
- freqtrade/user_data/backtest_results/phase03/backtest-result-2026-09-04_12-13-08.zip (baseline val)
- experiments/phase_03_freqai/results/val_trades_seed*.csv (FreqAI val)
- regime: phase02_analyze.compute_regime BİREBİR (kilitli tanım)

Çıktı: tuning47/diag415.json + stdout tabloları.
"""
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from scripts.phase02_analyze import compute_regime

D47 = ROOT / "experiments" / "phase_04_rl" / "tuning47"
BASELINE_ZIP = ROOT / "freqtrade/user_data/backtest_results/phase03/backtest-result-2026-09-04_12-13-08.zip"
FREQAI = ROOT / "experiments/phase_03_freqai/results"
SEEDS = [42, 7, 123, 2026, 999]
FEE, SLIP = 0.001, 0.0005
HORIZONS = [1, 3, 12, 36, 72, 240, 720]  # 5m x k => 5dk/15dk/1s/3s/6s/20s/60s
FOCUS_H = [1, 3, 12, 36, 72]  # rapor öncelikli ufuklar


def load_val():
    df = pd.read_feather(ROOT / "freqtrade/user_data/data/binance/BTC_USDT-5m.feather")
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)
    v = df[(df["date"] >= "2023-01-01") & (df["date"] <= "2023-06-30")].reset_index(drop=True)
    return df, v


def daily_regime_map(full_df):
    d = full_df.set_index("date").resample("1D").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    d = d.dropna()
    reg = compute_regime(d.copy())["regime"]
    return {k.date(): v for k, v in reg.items()}


def collapse(r):
    if r.startswith("bull"):
        return "bull"
    if r.startswith("bear"):
        return "bear"
    return r


def replay(actions, closes, stake0=100.0):
    """Env transition replay — phase49.replay ile birebir mantık."""
    off = len(closes) - len(actions) - 1
    assert off >= 0, (len(closes), len(actions))
    pos, entry, eq = False, None, stake0
    trades, pre_pos = [], []
    for k, a in enumerate(actions):
        ci = off + k
        pre_pos.append(1 if pos else 0)
        if not pos and a == 1:
            amount = eq * (1 - FEE) / (closes[ci] * (1 + SLIP))
            pos, entry, stake = True, (ci, closes[ci], amount, eq), eq
        elif pos and a == 2:
            o_k, o, amount, st = entry
            proceeds = amount * closes[ci] * (1 - SLIP) * (1 - FEE)
            fee = st * FEE + amount * closes[ci] * (1 - SLIP) * FEE
            slip = amount * SLIP * (o + closes[ci])
            trades.append({"open_idx": o_k, "close_idx": ci, "forced": False,
                           "open": o, "close": closes[ci], "stake": st,
                           "profit": proceeds - st, "fee": fee, "slip": slip,
                           "gross": amount * (closes[ci] - o)})
            eq += proceeds - st
            pos, entry, stake = False, None, None
    if pos:
        o_k, o, amount, st = entry
        k = len(closes) - 1
        c = closes[-1]
        proceeds = amount * c * (1 - SLIP) * (1 - FEE)
        fee = st * FEE + amount * c * (1 - SLIP) * FEE
        slip = amount * SLIP * (o + c)
        trades.append({"open_idx": o_k, "close_idx": k, "forced": True,
                       "open": o, "close": c, "stake": st,
                       "profit": proceeds - st, "fee": fee, "slip": slip,
                       "gross": amount * (c - o)})
        eq += proceeds - st
    return trades, pre_pos, eq, off


def fut_ret(closes, i, h):
    if h <= 0 or i + h >= len(closes):
        return np.nan
    return closes[i + h] / closes[i] - 1.0


def mfe_mae(closes, i, hmax):
    """Entry close başına, i+1..i+hmax penceresinde max/min exc. (entry close - baz)."""
    if i + 1 >= len(closes):
        return np.nan, np.nan
    end = min(i + hmax, len(closes) - 1)
    w = closes[i + 1:end + 1]
    if not len(w):
        return np.nan, np.nan
    return (w.max() / closes[i] - 1.0), (w.min() / closes[i] - 1.0)


def fr_stats(arr):
    arr = np.asarray([x for x in arr if x is not None and not np.isnan(x)], dtype=float)
    if len(arr) == 0:
        return {"n": 0}
    return {"n": int(len(arr)), "mean": round(float(arr.mean()), 5),
            "median": round(float(np.median(arr)), 5),
            "p_gt0": round(float((arr > 0).mean()), 4),
            "p_gt2bp": round(float((arr > 0.002).mean()), 4),
            "p_gt5bp": round(float((arr > 0.005).mean()), 4),
            "p_gt1pct": round(float((arr > 0.01).mean()), 4),
            "p_lt0": round(float((arr < 0).mean()), 4),
            "p_lt2bp": round(float((arr < -0.002).mean()), 4),
            "p_lt5bp": round(float((arr < -0.005).mean()), 4),
            "p_lt1pct": round(float((arr < -0.01).mean()), 4)}


def cohen_d(a, b):
    a = np.asarray([x for x in a if x is not None and not np.isnan(x)], dtype=float)
    b = np.asarray([x for x in b if x is not None and not np.isnan(x)], dtype=float)
    if len(a) < 2 or len(b) < 2:
        return None
    s = np.sqrt((len(a) * a.var(ddof=1) + len(b) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    if s == 0:
        return None
    return (a.mean() - b.mean()) / s


def two_sample_t(a, b):
    from scipy import stats
    a = np.asarray([x for x in a if x is not None and not np.isnan(x)], dtype=float)
    b = np.asarray([x for x in b if x is not None and not np.isnan(x)], dtype=float)
    if len(a) < 2 or len(b) < 2:
        return None
    t, p = stats.ttest_ind(a, b, equal_var=False)
    return {"t": round(float(t), 3), "p": round(float(p), 4)}


def main():
    full, vdf = load_val()
    closes = vdf["close"].values.astype(float)
    dates = pd.to_datetime(vdf["date"]).reset_index(drop=True)
    assert len(closes) - 30 - 1 == 51794, len(closes)
    day2reg = daily_regime_map(full)
    vdf["day"] = vdf["date"].dt.date
    vdf["regime"] = vdf["day"].map(day2reg)
    vdf["bucket"] = vdf["regime"].map(collapse)
    reg_days = vdf.drop_duplicates("day")["bucket"].value_counts().to_dict()
    reg_candles = vdf["bucket"].value_counts().to_dict()
    print("== validation rejim günleri (181 gün) ==", dict(reg_days))
    print("== validation rejim mumları (5m) ==", dict(reg_candles))

    out = {"seeds": {}, "baseline_forward": {}, "freqai_forward": {}, "random_ref": {},
           "buyhold": {}, "regime_days": {str(k): int(v) for k, v in reg_days.items()},
           "regime_candles": {str(k): int(v) for k, v in reg_candles.items()}}

    # ---- rassal/kontrol referans ve buy-hold (val penceresi, analitik) ----
    last = len(closes) - 1
    rng = np.random.default_rng(42)
    n_rand = 5000
    rand_idx = rng.integers(30, len(closes) - 1 - 720, size=n_rand)
    rand = {"idx": rand_idx.tolist()}
    for h in HORIZONS:
        rand[f"fr{h}"] = fr_stats([fut_ret(closes, int(i), h) for i in rand_idx])
    # rejim bazlı rastlantısal giriş (dir-market proxy)
    bull_idx = np.where(vdf["bucket"].values == "bull")[0]
    bull_idx = bull_idx[bull_idx <= len(closes) - 1 - 72]
    if len(bull_idx) > n_rand:
        bull_idx = rng.choice(bull_idx, size=n_rand, replace=False)
    rand["bull_cond"] = {}
    for h in HORIZONS:
        rand["bull_cond"][f"fr{h}"] = fr_stats([fut_ret(closes, int(i), h) for i in bull_idx])
    out["random_ref"] = rand
    out["buyhold"] = {"open": round(float(closes[30]), 2), "close": round(float(closes[-1]), 2),
                      "gross_pct": round(float(closes[-1] / closes[30] - 1) * 100, 2),
                      "net_pct_costly": round(float(((1 - FEE) / (1 + SLIP)) * (closes[-1] / closes[30]) * (1 - SLIP) * (1 - FEE) - 1) * 100, 2)}
    print("== buy & hold val referansı ==", out["buyhold"])

    # ---- baseline (zip) & FreqAI forward-return ----
    with zipfile.ZipFile(BASELINE_ZIP) as z:
        names = [n for n in z.namelist() if n.endswith(".json") and "config" not in n]
        btr = pd.DataFrame(json.loads(z.read(names[0]))["strategy"]["BaselineStrategy"]["trades"])
    btr["open_date"] = pd.to_datetime(btr["open_date"]).dt.tz_localize(None)
    bts = pd.to_datetime(btr["open_date"]).values
    b_idx = np.searchsorted(dates.values.astype("datetime64[s]"), bts.astype("datetime64[s]"))
    b_idx = np.clip(b_idx, 0, len(closes) - 1)
    for h in HORIZONS:
        out["baseline_forward"][f"fr{h}"] = fr_stats([fut_ret(closes, int(i), h) for i in b_idx])
    print("== baseline val forward-return (n=%d) ==" % len(b_idx),
          {h: out["baseline_forward"][f"fr{h}"]["mean"] for h in FOCUS_H})

    fcw = {}
    for s in SEEDS:
        fp = FREQAI / f"val_trades_seed{s}.csv"
        if not fp.exists():
            fcw[str(s)] = {"n": 0}
            continue
        f = pd.read_csv(fp)
        f["open_date"] = pd.to_datetime(f["open_date"]).dt.tz_localize(None)
        fm = (f["open_date"] >= "2023-01-01") & (f["open_date"] <= "2023-06-30")
        f = f[fm]
        oi = np.searchsorted(dates.values.astype("datetime64[s]"),
                             f["open_date"].values.astype("datetime64[s]"))
        oi = np.clip(oi, 0, len(closes) - 1)
        row = {"n": int(len(oi)),
               "net": round(float(f["profit_abs"].sum()), 2) if "profit_abs" in f else None}
        for h in HORIZONS:
            row[f"fr{h}"] = fr_stats([fut_ret(closes, int(i), h) for i in oi])
        fcw[str(s)] = row
    out["freqai_forward"] = fcw
    print("== FreqAI val forward-return (n per seed) ==",
          {k: (v["n"], round(v["fr72"]["mean"], 5) if v.get("fr72") else None) for k, v in fcw.items()})

    # ---- seed bazlı analiz ----
    for s in SEEDS:
        art = json.load(open(D47 / f"art_E1_seed{s}.json", encoding="utf-8"))
        acts = np.asarray(art["actions"])
        eqs = np.asarray(art["equities"])
        rews = np.asarray(art["rewards"])
        trades, pre_pos, f_eq, off = replay(acts, closes)
        assert abs(f_eq - 100.0 - sum(t["profit"] for t in trades)) < 0.05
        assert len(pre_pos) == len(acts)
        sid = out["seeds"][str(s)] = {}

        trades_df = pd.DataFrame(trades)
        hold_min = (trades_df["close_idx"] - trades_df["open_idx"]) * 5 if len(trades_df) else pd.Series(dtype=float)
        net = float(trades_df["profit"].sum()) if len(trades_df) else 0.0
        sid["n_trades"] = int(len(trades))
        sid["net"] = round(net, 3)
        sid["gross"] = round(float(trades_df["gross"].sum()), 3) if len(trades_df) else 0.0
        sid["fee"] = round(float(trades_df["fee"].sum()), 3) if len(trades_df) else 0.0
        sid["slip"] = round(float(trades_df["slip"].sum()), 3) if len(trades_df) else 0.0
        sid["forced"] = int(trades_df["forced"].sum()) if len(trades_df) else 0
        sid["wr"] = round(float((trades_df["profit"] > 0).mean()), 4) if len(trades_df) else 0.0
        sid["hold_min"] = {"median": round(float(hold_min.median()), 1) if len(hold_min) else 0.0,
                           "mean": round(float(hold_min.mean()), 1) if len(hold_min) else 0.0,
                           "max": round(float(hold_min.max()), 1) if len(hold_min) else 0.0}
        act_counts = {str(int(a)): int((acts == a).sum()) for a in (0, 1, 2)}
        sid["actions"] = act_counts
        sid["in_position_frac"] = round(float(np.mean(pre_pos)), 4)
        valid_buy = [t for t in trades]
        buy_dates = dates.iloc[[t["open_idx"] for t in valid_buy]].dt.date.tolist()
        sid["exposure_by_regime"] = {}
        pos_series = pd.Series(pre_pos)
        acts_bucket = vdf["bucket"].iloc[off:off + len(acts)].reset_index(drop=True)
        ab = pd.DataFrame({"a": acts, "pos": pos_series, "b": acts_bucket})
        for b, g in ab.groupby("b"):
            sid["exposure_by_regime"][b] = {
                "n": int(len(g)), "pos_frac": round(float(g["pos"].mean()), 4),
                "buy": int((g["a"] == 1).sum()), "sell": int((g["a"] == 2).sum())}
        # policy signature: trade frekansı
        sid["trades_per_day"] = round(len(trades) / 181, 2)

        # ---- her trade için detay + future return ----
        rows = []
        for t in trades:
            i, e = t["open_idx"], t["close_idx"]
            drow = {"open_idx": i, "close_idx": e, "forced": bool(t["forced"]),
                    "open_date": str(dates.iloc[i])[:16], "close_date": str(dates.iloc[e])[:16],
                    "entry_price": round(t["open"], 2), "exit_price": round(t["close"], 2),
                    "hold_candles": e - i, "hold_min": (e - i) * 5,
                    "net_pnl": round(t["profit"], 4), "net_ret": round(t["profit"] / t["stake"], 5),
                    "gross": round(t["gross"], 4), "fee": round(t["fee"], 4), "slip": round(t["slip"], 4),
                    "stake": round(t["stake"], 4),
                    "regime_entry": collapse(vdf["regime"].iloc[i]),
                    "regime_exit": collapse(vdf["regime"].iloc[e]) if e < len(vdf) else "end",
                    "regime_full": vdf["regime"].iloc[i]}
            for h in HORIZONS:
                drow[f"fr{h}"] = round(fut_ret(closes, i, h), 6) if not np.isnan(fut_ret(closes, i, h)) else None
            mfe_h, mae_h = mfe_mae(closes, i, e - i)
            mfe72, mae72 = mfe_mae(closes, i, 72)
            drow["mfe_hold"] = round(mfe_h, 6) if not np.isnan(mfe_h) else None
            drow["mae_hold"] = round(mae_h, 6) if not np.isnan(mae_h) else None
            drow["mfe_72"] = round(mfe72, 6) if not np.isnan(mfe72) else None
            drow["mae_72"] = round(mae72, 6) if not np.isnan(mae72) else None
            rows.append(drow)
        tdf = pd.DataFrame(rows)
        sid["trades"] = rows

        # ---- BUY future-return istatistikleri ----
        sid["buy_fr"] = {}
        for h in FOCUS_H + [240, 720]:
            sid["buy_fr"][f"fr{h}"] = fr_stats([r[f"fr{h}"] for r in rows])

        # ---- SELL sonrası future-return (valid SELL'ler) ----
        sell_candles = [t["close_idx"] for t in trades if not t["forced"]]
        sid["sell_fr"] = {}
        sf = {"n": len(sell_candles)}
        for h in FOCUS_H:
            vals = [fut_ret(closes, c, h) for c in sell_candles]
            vals = [x for x in vals if not np.isnan(x)]
            sf[f"fr{h}"] = fr_stats(vals)
        sid["sell_fr"] = sf

        # ---- entry-quality eşikleri (+12 ve +72) ----
        for hkey in ("fr12", "fr72"):
            h = int(hkey[2:])
            g = {}
            for lo, hi, lab in [(-np.inf, -0.01, "lt_-1pct"), (-0.01, -0.005, "btw_-1_-0.5pct"),
                                (-0.005, -0.002, "btw_-0.5_-0.2pct"), (-0.002, 0.0, "btw_-0.2_0pct"),
                                (0.0, 0.002, "btw_0_0.2pct"), (0.002, 0.005, "btw_0.2_0.5pct"),
                                (0.005, 0.01, "btw_0.5_1pct"), (0.01, np.inf, "gt_1pct")]:
                vals = [r[hkey] for r in rows if r[hkey] is not None and lo < r[hkey] <= hi]
                g[lab] = {"n": len(vals),
                          "mean": round(float(np.mean(vals)), 5) if vals else None,
                          "median": round(float(np.median(vals)), 5) if vals else None}
            sid[f"entry_quality_{hkey}"] = g

        # ---- konsantrasyon ----
        if len(trades_df):
            prof = trades_df["profit"]
            top_n = prof.sort_values(ascending=False)
        else:
            prof, top_n = pd.Series(dtype=float), pd.Series(dtype=float)
        def share(k):
            if not len(prof) or net == 0:
                return None
            return round(float(top_n.head(k).sum()) / net, 4)
        sid["conc_top1_share_of_net"] = share(1)
        sid["conc_top3_share_of_net"] = share(3)
        sid["conc_top5_share_of_net"] = share(5)
        sid["top3_net"] = round(float(top_n.head(3).sum()), 3) if len(prof) else 0.0
        sid["top5_net"] = round(float(top_n.head(5).sum()), 3) if len(prof) else 0.0
        sid["net_ex_top3"] = round(net - float(top_n.head(3).sum()), 3)
        sid["net_ex_top5"] = round(net - float(top_n.head(5).sum()), 3)
        # en uzun hold
        hidx = int(trades_df["close_idx"].sub(trades_df["open_idx"]).idxmax()) if len(trades_df) else None
        if hidx is not None:
            lh = trades_df.iloc[hidx]
            sid["longest_hold"] = {"hold_min": int((lh["close_idx"] - lh["open_idx"]) * 5),
                                   "net": round(float(lh["profit"]), 3),
                                   "open_idx": int(lh["open_idx"])}
        # rejim katkısı (trade bazlı)
        reg_contrib = {}
        if len(tdf):
            for b, g in tdf.groupby("regime_entry"):
                reg_contrib[b] = {"n": int(len(g)), "net": round(float(g["net_pnl"].sum()), 3),
                                  "net_share_of_total": round(float(g["net_pnl"].sum() / net), 4) if net else None}
        sid["regime_contrib"] = reg_contrib
        # top-3 trade bilgisi
        if len(trades_df):
            top3 = trades_df.sort_values("profit", ascending=False).head(3)
            sid["top3_trades"] = [{"open_idx": int(r.open_idx), "close_idx": int(r.close_idx),
                                   "net": round(float(r.profit), 3), "hold_min": int((r.close_idx - r.open_idx) * 5),
                                   "regime_entry": collapse(vdf["regime"].iloc[r.open_idx])}
                                  for r in top3.itertuples()]
        else:
            sid["top3_trades"] = []

        # ---- RL vs random karşılaştırma ----
        rl72 = [r["fr72"] for r in rows if r["fr72"] is not None]
        rnd72 = [fut_ret(closes, int(i), 72) for i in rand_idx]
        sid["vs_random"] = {
            "cohen_d_fr72": round(cohen_d(rl72, rnd72), 4) if cohen_d(rl72, rnd72) is not None else None,
            "ttest_fr72": two_sample_t(rl72, rnd72),
            "mean_rl": round(float(np.mean(rl72)), 5) if rl72 else None,
            "mean_rand": round(float(np.mean(rnd72)), 5)}
        rl1 = [r["fr1"] for r in rows if r["fr1"] is not None]
        rnd1 = [fut_ret(closes, int(i), 1) for i in rand_idx]
        sid["vs_random_fr1"] = {
            "cohen_d": round(cohen_d(rl1, rnd1), 4) if cohen_d(rl1, rnd1) is not None else None,
            "ttest": two_sample_t(rl1, rnd1)}

        # equity uyum
        sid["recon"] = {"replay_final": round(f_eq, 3), "saved_final": round(float(eqs[-1]), 3),
                        "sum_rewards_log": round(float(np.log(eqs[-1] / 100.0)), 6)}

        print(f"\n===== E1 seed {s} =====")
        print(f" trades={len(trades)} net={net:.2f} gross={sid['gross']} fee={sid['fee']} slip={sid['slip']} "
              f"WR={sid['wr']} forced={sid['forced']}")
        print(f" hold_min med/mean/max = {sid['hold_min']}")
        print(f" actions H/B/S = {act_counts} in-pos frac = {sid['in_position_frac']} trades/day = {sid['trades_per_day']}")
        for b, x in sid["exposure_by_regime"].items():
            print(f"   regime {b}: n={x['n']} pos_frac={x['pos_frac']} buy={x['buy']} sell={x['sell']}")
        print(" BUY future-return:")
        for h in FOCUS_H:
            st = sid["buy_fr"][f"fr{h}"]
            if st["n"] == 0:
                print(f"   +{h:>3} candle: yok (trade yok)")
                continue
            print(f"   +{h:>3} candle ({(h*5):>4}dk): mean={st['mean']} med={st['median']} "
                  f"P>0={st['p_gt0']} P>+1%={st['p_gt1pct']} P<-1%={st['p_lt1pct']}")
        print(" SELL sonrası future-return (valid):",
          {f"fr{h}": (sid["sell_fr"][f"fr{h}"].get("mean") if sid["sell_fr"][f"fr{h}"].get("n") else None)
           for h in FOCUS_H})
        print(" konsantrasyon: top1=%s top3=%s top5=%s net_ex_top3=%s net_ex_top5=%s" % (
            sid["conc_top1_share_of_net"], sid["conc_top3_share_of_net"],
            sid["conc_top5_share_of_net"], sid["net_ex_top3"], sid["net_ex_top5"]))
        print(" longhold:", sid.get("longest_hold"))
        print(" regime_contrib:", {k: (v["n"], v["net"]) for k, v in reg_contrib.items()})
        print(" vs_random:", sid["vs_random"])

    json.dump(out, open(D47 / "diag415.json", "w", encoding="utf-8"), indent=2, default=str)
    print("\nYazıldı: tuning47/diag415.json")


if __name__ == "__main__":
    main()