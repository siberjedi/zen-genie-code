"""Phase 3.6 — Frozen prediction execution study (DIAGNOSTIC ONLY).

Kilitler: eğitim YOK, feature/label/model/hyperparameter YOK, Final Test A YOK
(okuma bile yok), Phase 3 sonucu OVERWRITE YOK, protokol/threshold/baseline YOK.
SADECE validation penceresi + dondurulmuş rf_seed2026 + mevcut proba mantığı.

Kullanım:
  py -3 scripts/phase36_exec_study.py --parts h1
  py -3 scripts/phase36_exec_study.py --parts hold cool
  py -3 scripts/phase36_exec_study.py --parts h5
Sonuçlar results/exec_study.csv'ye artımlı birleşir. Hiçbir variant "strateji" değildir.
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd

from scripts.phase03_experiment import (build_panel, ELIGIBLE_18, MODEL_DIR,
                                        metrics_from_trades, FEE, MAX_OPEN,
                                        START_WALLET)
from src.freqai.features import FEATURES
from src.freqai.splits import (slice_frame, VAL_START, VAL_END, FINAL_A_START,
                               assert_no_final_leak)
from src.freqai.model import predict_proba

RES_DIR = ROOT / "experiments" / "phase_03_freqai" / "results"
SEED = 2026
VAL_DAYS = 181


def load_val_proba():
    """Dondurulmuş model + validation paneli -> pair -> df[date,open,high,low,close,proba]."""
    model = joblib.load(MODEL_DIR / f"rf_seed{SEED}.joblib")
    panel = build_panel(ELIGIBLE_18, end=VAL_END)
    out = {}
    for pair, df in panel.items():
        s = slice_frame(df, VAL_START, VAL_END)
        assert_no_final_leak(s["date"], f"exec-{pair}")
        assert (s["date"] < FINAL_A_START).all()
        if len(s) == 0:
            continue
        proba = predict_proba(model, s[FEATURES].values)
        base = df[["date", "open", "high", "low", "close"]].copy()
        m = base.merge(s[["date"]].assign(proba=proba), on="date", how="inner")
        out[pair] = m.sort_values("date").reset_index(drop=True)
    return out


def simulate_var(panel, entry_thr=0.5, exit_thr=0.5, min_hold_min=0,
                 cooldown_min=0, allow_same_candle_reentry=True):
    """Parametrik simülasyon. entry_thr==exit_thr==0.5 + kısıtsız = frozen davranış.

    - Gösterge sinyali stateful: flat iken proba>entry_thr -> 1;
      sinyal-long iken proba<exit_thr -> 0. (entry_thr==exit_thr ise statik sinyale indirgenir.)
    - min_hold: SADECE sinyal çıkışını bloklar (SL/ROI her zaman aktif).
    - cooldown: çıkış sonrası aynı pair'de dakika cinsinden giriş yasağı.
    - allow_same_candle_reentry=False: çıkış yapılan mumda giriş yok (H5).
    """
    wallet = START_WALLET
    open_pos, last_exit, sig_state, trades = {}, {}, {}, []
    idx = {p: {t: i for i, t in enumerate(df["date"])} for p, df in panel.items()}
    all_ts = sorted(set().union(*[set(d["date"]) for d in panel.values()]))
    for t in all_ts:
        exited_here = set()
        for pair in sorted(panel):
            df = panel[pair]
            i = idx[pair].get(t)
            if i is None:
                continue
            row = df.iloc[i]
            st = sig_state.get(pair, 0)
            if st == 0 and row["proba"] >= entry_thr:
                st = 1
            elif st == 1 and row["proba"] < exit_thr:
                st = 0
            sig_state[pair] = st
        for pair in sorted(open_pos):
            df = panel[pair]
            i = idx[pair].get(t)
            if i is None:
                continue
            row = df.iloc[i]
            pos = open_pos[pair]
            px, reason = None, None
            if row["low"] <= pos["entry"] * 0.90:
                px, reason = pos["entry"] * 0.90, "stop_loss"
            elif row["high"] >= pos["entry"] * 1.02:
                px, reason = pos["entry"] * 1.02, "roi"
            elif sig_state.get(pair, 0) == 0 and (t - pos["entry_time"]).total_seconds() / 60 >= min_hold_min:
                px, reason = row["close"], "exit_signal"
            if px is not None:
                gross = (px - pos["entry"]) * pos["amount"]
                fee = pos["entry"] * pos["amount"] * FEE + px * pos["amount"] * FEE
                profit_abs = gross - fee
                trades.append({"pair": pair, "open_date": pos["entry_time"], "close_date": t,
                               "open_rate": pos["entry"], "close_rate": px,
                               "stake_amount": pos["stake"], "profit_abs": profit_abs,
                               "profit_ratio": profit_abs / pos["stake"],
                               "exit_reason": reason, "fee": fee, "gross": gross})
                wallet += profit_abs
                del open_pos[pair]
                last_exit[pair] = t
                exited_here.add(pair)
        if len(open_pos) < MAX_OPEN:
            for pair in sorted(panel):
                if len(open_pos) >= MAX_OPEN or pair in open_pos:
                    continue
                df = panel[pair]
                i = idx[pair].get(t)
                if i is None:
                    continue
                row = df.iloc[i]
                if sig_state.get(pair, 0) != 1:
                    continue
                if not allow_same_candle_reentry and pair in exited_here:
                    continue
                if pair in last_exit and (t - last_exit[pair]).total_seconds() / 60 < cooldown_min:
                    continue
                px = row["close"]
                stake = wallet * 0.99 / MAX_OPEN
                open_pos[pair] = {"entry": px, "amount": stake / px,
                                  "stake": stake, "entry_time": t}
    for pair, pos in sorted(open_pos.items()):
        df = panel[pair]
        px = df.iloc[-1]["close"]
        gross = (px - pos["entry"]) * pos["amount"]
        fee = pos["entry"] * pos["amount"] * FEE + px * pos["amount"] * FEE
        profit_abs = gross - fee
        trades.append({"pair": pair, "open_date": pos["entry_time"],
                       "close_date": df.iloc[-1]["date"], "open_rate": pos["entry"],
                       "close_rate": px, "stake_amount": pos["stake"],
                       "profit_abs": profit_abs, "profit_ratio": profit_abs / pos["stake"],
                       "exit_reason": "force_exit", "fee": fee, "gross": gross})
        wallet += profit_abs
    # sinyal kolonu: statik 0.5 referansı (karşılaştırılabilirlik için ayrıca saklanır)
    return trades


def run_variant(panel, name, family, **kw):
    trades = simulate_var(panel, **kw)
    met = metrics_from_trades(
        [{k: tr[k] for k in ("pair", "open_date", "close_date", "open_rate", "close_rate",
                             "stake_amount", "profit_abs", "profit_ratio", "exit_reason")}
         for tr in trades], VAL_START, VAL_END)
    df = pd.DataFrame(trades)
    if len(df):
        df["open_date"] = pd.to_datetime(df["open_date"])
        df["close_date"] = pd.to_datetime(df["close_date"])
        hold = (df["close_date"] - df["open_date"]).dt.total_seconds() / 60
        med_hold, avg_hold = float(hold.median()), float(hold.mean())
        gross, fee = float(df["gross"].sum()), float(df["fee"].sum())
    else:
        med_hold = avg_hold = gross = fee = 0.0
    row = {"variant": name, "family": family,
           "entry_thr": kw.get("entry_thr", 0.5), "exit_thr": kw.get("exit_thr", 0.5),
           "min_hold": kw.get("min_hold_min", 0), "cooldown": kw.get("cooldown_min", 0),
           "reentry": kw.get("allow_same_candle_reentry", True),
           "trades": met["trade_count"], "trades_day": round(met["trade_count"] / VAL_DAYS, 2),
           "gross": round(gross, 2), "fees": round(fee, 2), "net": met["net_abs"],
           "sharpe": met["daily_sharpe"], "maxdd": met["max_dd"],
           "pf": met["profit_factor"], "wr": met["win_rate"],
           "med_hold": round(med_hold, 1), "avg_hold": round(avg_hold, 1),
           "gross_per_trade": round(gross / len(df), 4) if len(df) else 0.0,
           "fee_per_trade": round(fee / len(df), 4) if len(df) else 0.0,
           "gross_fee_ratio": round(gross / fee, 3) if fee else 0.0,
           "turnover": met["turnover"], "volume": met["total_volume"]}
    print(f"[{name}] n={row['trades']} gross={row['gross']} fee={row['fees']} "
          f"net={row['net']} sharpe={row['sharpe']} dd={row['maxdd']} "
          f"medhold={row['med_hold']}", flush=True)
    return row


VARIANTS = {
    "h1": [("A_base_50_50", "h1", {}),
           ("B_55_45", "h1", {"entry_thr": 0.55, "exit_thr": 0.45}),
           ("C_60_40", "h1", {"entry_thr": 0.60, "exit_thr": 0.40})],
    "hold": [("hold_05", "h2_hold", {"min_hold_min": 5}),
             ("hold_15", "h2_hold", {"min_hold_min": 15}),
             ("hold_30", "h2_hold", {"min_hold_min": 30}),
             ("hold_60", "h2_hold", {"min_hold_min": 60})],
    "cool": [("cool_00", "h2_cool", {"cooldown_min": 0}),
             ("cool_15", "h2_cool", {"cooldown_min": 15}),
             ("cool_30", "h2_cool", {"cooldown_min": 30}),
             ("cool_60", "h2_cool", {"cooldown_min": 60})],
    "h5": [("reentry_off", "h5", {"allow_same_candle_reentry": False})],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", nargs="*", default=["h1", "hold", "cool", "h5"])
    args = ap.parse_args()
    panel = load_val_proba()
    print(f"panel: {len(panel)} pair", flush=True)
    out = RES_DIR / "exec_study.csv"
    old = pd.read_csv(out) if out.exists() else pd.DataFrame()
    rows = []
    for part in args.parts:
        for name, fam, kw in VARIANTS[part]:
            if len(old) and name in set(old["variant"]):
                print(f"[{name}] atlaniyor (kayitli)", flush=True)
                continue
            rows.append(run_variant(panel, name, fam, **kw))
    if rows:
        new = pd.DataFrame(rows)
        if len(old):
            new = pd.concat([old[~old["variant"].isin(new["variant"])], new],
                            ignore_index=True)
        new.to_csv(out, index=False)
        print(f"yazildi: {out} ({len(new)} variant)", flush=True)
    # repro check: A_base_50_50 frozen sonuca esit olmali
    if "A_base_50_50" in set(pd.read_csv(out)["variant"]):
        a = pd.read_csv(out).set_index("variant").loc["A_base_50_50"]
        ref = pd.read_csv(RES_DIR / "val_metrics.csv")
        ref = ref[ref["seed"] == 2026].iloc[0]
        ok = (int(a["trades"]) == int(ref["trade_count"])
              and abs(float(a["net"]) - float(ref["net_abs"])) < 0.01)
        print(f"REPRO frozen==A: {'PASS' if ok else 'FAIL-ABORT'} "
              f"({a['trades']}/{ref['trade_count']}, {a['net']}/{ref['net_abs']})", flush=True)
        if not ok:
            raise SystemExit("Variant A frozen sonucu tutmuyor — ABORT")


if __name__ == "__main__":
    main()
