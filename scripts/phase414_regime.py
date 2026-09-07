"""Phase 4.14 REGIME ANALYSIS — READ-ONLY (eğitim yok, tuning yok, Final B yok).

Girdi (mevcut artifact'lar, salt-okunur):
- tuning47/art_E1_seed*.json (aksiyon/equity) + run_E1_*.json (metrikler)
- pilot411/art_B1/B2_*.json + run_B1/B2_*.json
- h1_realized/trades_R1_*.json (tarihli trade'ler)
- backtest zip 12-13-08 (baseline validation trade'leri)
- phase_03_freqai/results/val_trades_seed*.csv (FreqAI validation)
- BTC feather (fiyat/tarih okuma)
Rejim: phase02_analyze.compute_regime BİREBİR (kilitli tanım, yeni icat YOK).
Trade replay: phase49_analyze.replay BİREBİR (deterministik rekonstrüksiyon).
Çıktı: tuning47/regime414.json (küçük) + stdout tabloları.
"""
import glob
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from scripts.phase02_analyze import compute_regime
from scripts.phase49_analyze import replay

D47 = ROOT / "experiments" / "phase_04_rl" / "tuning47"
P411 = ROOT / "experiments" / "phase_04_rl" / "pilot411"
SEEDS = [42, 7, 123, 2026, 999]
FEE, SLIP = 0.001, 0.0005


def collapse(r):
    if r.startswith("bull"):
        return "bull"
    if r.startswith("bear"):
        return "bear"
    return r  # sideways / sideways_high_vol / unknown ayri kalir


def load_val():
    df = pd.read_feather(ROOT / "freqtrade/user_data/data/binance/BTC_USDT-5m.feather")
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    return df.sort_values("date").reset_index(drop=True)


def daily_regime(full_df):
    d = full_df.set_index("date").resample("1D").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    d = d.dropna()
    r = compute_regime(d.copy())
    return r["regime"]  # Timestamp -> granular label


def replay_e1(actions, closes):
    trades, pre_pos, _eq = replay(actions, closes, None)
    return trades, pre_pos


def trade_stats(trades):
    """trades: list of dicts with profit/fee/slip/gross/open_idx/close_idx/forced."""
    import datetime
    df = pd.DataFrame(trades)
    if not len(df):
        return {"n": 0}
    df["hold_min"] = (df["close_idx"] - df["open_idx"]) * 5
    rets = df["profit"] / df["stake"]
    return {"n": int(len(df)), "gross": round(float(df["gross"].sum()), 2),
            "fee": round(float(df["fee"].sum()), 2),
            "slip": round(float(df["slip"].sum()), 2),
            "net": round(float(df["profit"].sum()), 2),
            "wr": round(float((df["profit"] > 0).mean()), 4),
            "avg_ret": round(float(rets.mean()), 5),
            "med_hold": round(float(df["hold_min"].median()), 1),
            "forced_n": int(df["forced"].sum())}


def main():
    full = load_val()
    vdf = full[(full["date"] >= "2023-01-01") & (full["date"] <= "2023-06-30")].reset_index(drop=True)
    closes = vdf["close"].values
    assert len(closes) - 30 - 1 == 51794, len(closes)
    reg = daily_regime(full)
    vreg = reg["2023-01-01":"2023-06-30"]
    # örneklem büyüklükleri
    vc = vreg.value_counts()
    print("== validation rejim günleri (181 gün) ==", flush=True)
    for k, v in vc.items():
        print(f"  {k}: {v} gün", flush=True)
    # mum sayımı
    vdf["day"] = vdf["date"].dt.date
    day2reg = {d.date(): r for d, r in vreg.items()}
    vdf["regime"] = vdf["day"].map(day2reg)
    print("== rejim mum sayıları (5m) ==", flush=True)
    for k, v in vdf["regime"].value_counts().items():
        print(f"  {k}: {v} mum", flush=True)

    out = {"regime_days": {str(k): int(v) for k, v in vc.items()},
           "regime_candles": {str(k): int(v) for k, v in vdf["regime"].value_counts().items()},
           "E1": {}, "B": {}, "R1": {}, "baseline": {}, "freqai": {}}

    # ---- E1: replay + attribution ----
    for s in SEEDS:
        a = json.load(open(D47 / f"art_E1_seed{s}.json", encoding="utf-8"))
        acts = a["actions"]
        trades, pre_pos = replay_e1(acts, closes)
        rows = []
        for t in trades:
            # open_idx aksiyon uzayında; df indeksine çevir (off=30: phase49 bulgusu)
            o_di = t["open_idx"] + 30
            d = vdf["date"].iloc[o_di].date()
            rows.append({**t, "reg": vdf["regime"].iloc[o_di], "bucket": collapse(vdf["regime"].iloc[o_di])})
        df = pd.DataFrame(rows)
        by = {}
        if len(df):
            for b, g in df.groupby("bucket"):
                by[b] = trade_stats(g.to_dict("records"))
                by[b]["trades_idx"] = [int(i) for i in g.index]
        # aksiyon dağılımı + pozisyonlu süre (rejim bazında)
        acts_s = pd.Series(acts)
        pos_s = pd.Series(pre_pos)
        # aksiyon k -> df idx 30+k -> regime
        adates = [vdf["regime"].iloc[30 + k] for k in range(len(acts))]
        adf = pd.DataFrame({"a": acts, "pre": pre_pos, "bucket": [collapse(x) for x in adates]})
        ab = {}
        for b, g in adf.groupby("bucket"):
            ab[b] = {"n": int(len(g)),
                     "buy": int((g["a"] == 1).sum()), "sell": int((g["a"] == 2).sum()),
                     "hold": int((g["a"] == 0).sum()),
                     "pos_held_frac": round(float(g["pre"].mean()), 4)}
        # günlük equity attribution (saved art equities)
        eq = np.array(a["equities"])
        # equity eğrisi aksiyon başına; güne indirgemek için replay pozisyonu yerine
        # trade P&L'ini kapanış gününe yaz (trade-bazlı, şeffaf)
        out["E1"][str(s)] = {"by_bucket": by, "actions": ab,
                             "n_trades": len(rows),
                             "forced_n": int(df["forced"].sum()) if len(df) else 0}
        print(f"E1/{s}: " + ("zero-trade" if not by else " | ".join(
            f"{b}: n={by[b]['n']} net={by[b]['net']}" for b in sorted(by))), flush=True)

    # ---- B1/B2 (destekleyici) ----
    for cid in ["B1", "B2"]:
        out["B"][cid] = {}
        for s in SEEDS:
            p = P411 / f"art_{cid}_seed{s}.json"
            if not p.exists():
                continue
            a = json.load(open(p, encoding="utf-8"))
            trades, pre_pos = replay_e1(a["actions"], closes)
            rows = []
            for t in trades:
                o_di = t["open_idx"] + 30
                rows.append({**t, "bucket": collapse(vdf["regime"].iloc[o_di])})
            df = pd.DataFrame(rows)
            by = {}
            if len(df):
                for b, g in df.groupby("bucket"):
                    by[b] = trade_stats(g.to_dict("records"))
            out["B"][cid][str(s)] = {"by_bucket": by, "n_trades": len(rows)}
        print(f"{cid}: " + "; ".join(
            f"s{s}: " + ",".join(f"{b}={out['B'][cid][str(s)]['by_bucket'][b]['net']}"
                                 for b in sorted(out["B"][cid][str(s)]["by_bucket"]))
            for s in SEEDS), flush=True)

    # ---- R1 (kayıtlı trade tarihleri) ----
    for s in SEEDS:
        tr = json.load(open(ROOT / f"experiments/phase_04_rl/h1_realized/trades_R1_seed{s}.json",
                            encoding="utf-8"))
        for t in tr:
            d = pd.Timestamp(t["open_date"]).date()
            t["bucket"] = collapse(day2reg.get(d, "unknown"))
            # phase49 replay alan adlarına çevir
            t["profit"] = t["profit_abs"]
            t["stake"] = t["stake_amount"]
            t["fee"] = t.get("fee_paid", 0.0)
            t["slip"] = t.get("slip_paid", 0.0)
            t["gross"] = t.get("gross", 0.0)
            t["open_idx"] = 0
            t["close_idx"] = int(round(t.get("hold_min", 0) / 5)) if t.get("hold_min") else 0
            t["forced"] = (t.get("exit_reason") == "forced_close")
        df = pd.DataFrame(tr)
        by = {}
        if len(df):
            for b, g in df.groupby("bucket"):
                by[b] = trade_stats(g.to_dict("records"))
        out["R1"][str(s)] = {"by_bucket": by, "n_trades": len(tr)}
        print(f"R1/{s}: " + " | ".join(
            f"{b}: n={by[b]['n']} net={by[b]['net']}" for b in sorted(by)), flush=True)

    # ---- baseline validation zIP (12-13-08) ----
    import zipfile
    zpath = ROOT / "freqtrade/user_data/backtest_results/phase03/backtest-result-2026-09-04_12-13-08.zip"
    z = zipfile.ZipFile(zpath)
    n = [x for x in z.namelist() if x.endswith(".json") and "config" not in x][0]
    btr = pd.DataFrame(json.loads(z.read(n))["strategy"]["BaselineStrategy"]["trades"])
    btr["open_date"] = pd.to_datetime(btr["open_date"]).dt.tz_localize(None)
    btr["bucket"] = btr["open_date"].dt.date.map(
        lambda d: collapse(day2reg.get(d, "out_of_window")))
    print("baseline val: n=%d window-dışı=%d" % (
        len(btr), int((btr["bucket"] == "out_of_window").sum())), flush=True)
    btr["profit"] = btr["profit_abs"]
    btr["stake"] = btr["stake_amount"]
    btr["fee"] = 0.0  # backtest fee trade kaydında ayrı değil; toplam fee raporda
    btr["slip"] = 0.0
    btr["gross"] = btr["profit_abs"]
    btr["open_idx"] = 0
    btr["close_idx"] = 0
    btr["forced"] = False
    by = {}
    for b, g in btr[btr["bucket"] != "out_of_window"].groupby("bucket"):
        by[b] = trade_stats(g.to_dict("records"))
    out["baseline"] = {"by_bucket": by, "n_trades": int((btr["bucket"] != "out_of_window").sum()),
                       "n_out_of_window": int((btr["bucket"] == "out_of_window").sum())}
    print("baseline: " + " | ".join(
        f"{b}: n={by[b]['n']} net={by[b]['net']}" for b in sorted(by)), flush=True)

    # ---- FreqAI (selected seed 2026 + bağlam için diğerleri: sayı/net) ----
    for s in [2026, 42, 7, 123, 999]:
        p = ROOT / f"experiments/phase_03_freqai/results/val_trades_seed{s}.csv"
        if not p.exists():
            continue
        f = pd.read_csv(p)
        f["open_date"] = pd.to_datetime(f["open_date"]).dt.tz_localize(None)
        f["bucket"] = f["open_date"].dt.date.map(
            lambda d: collapse(day2reg.get(d, "out_of_window")))
        f["profit"] = f["profit_abs"]
        f["stake"] = f["stake_amount"]
        f["fee"] = 0.0
        f["slip"] = 0.0
        f["gross"] = f["profit_abs"]
        f["open_idx"] = 0
        f["close_idx"] = 0
        f["forced"] = False
        by = {}
        sub = f[f["bucket"] != "out_of_window"]
        for b, g in sub.groupby("bucket"):
            by[b] = trade_stats(g.to_dict("records"))
        out["freqai"][str(s)] = {"by_bucket": by, "n_trades": int(len(sub)),
                                 "n_out_of_window": int((f["bucket"] == "out_of_window").sum())}
    print("freqai/2026: " + " | ".join(
        f"{b}: n={out['freqai']['2026']['by_bucket'][b]['n']} "
        f"net={out['freqai']['2026']['by_bucket'][b]['net']}"
        for b in sorted(out["freqai"]["2026"]["by_bucket"])), flush=True)

    json.dump(out, open(D47 / "regime414.json", "w", encoding="utf-8"), indent=2)
    print("yazıldı: regime414.json", flush=True)


if __name__ == "__main__":
    main()
