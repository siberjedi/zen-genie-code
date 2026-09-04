"""Phase 3 deneyi — ONAYLI koşum (2026-09-04).

Dondurulmuş konfigürasyon: 8 feature, label H=12/thr=0.002, RF(200/8/50/balanced/n_jobs=1),
5 seed, train 2020-01-01->2022-12-31, validation 2023-01-01->2023-06-30.
Final Test A'ya DOKUNMAZ (bu script Final A tarihlerini reddeder).

Kullanım:
  py -3 scripts/phase03_experiment.py --seeds 42 7 123 2026 999   # validation koşumları
  py -3 scripts/phase03_experiment.py --cv                        # 5 CV fold (seed 42)
Sonuçlar artımlı yazılır (crash-safe). Sonuçlara göre config DEĞİŞMEZ.
"""
import argparse
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.freqai.features import build_features, FEATURES
from src.freqai.labels import build_labels
from src.freqai.splits import (slice_frame, assert_no_final_leak, calendar_folds,
                               TRAIN_START, TRAIN_END, VAL_START, VAL_END,
                               FINAL_A_START, SEEDS)
from src.freqai.model import make_model, predict_proba
from src.data.metrics import sharpe, sortino

ELIGIBLE_18 = ["BTC/USDT", "ETH/USDT", "XRP/USDT", "ADA/USDT", "BNB/USDT",
               "DOGE/USDT", "TRX/USDT", "ZEC/USDT", "LINK/USDT", "SOL/USDT",
               "AVAX/USDT", "UNI/USDT", "AAVE/USDT", "NEAR/USDT", "ARB/USDT",
               "PROM/USDT", "SUI/USDT", "PEPE/USDT"]
DATA_DIR = ROOT / "freqtrade" / "user_data" / "data" / "binance"
RES_DIR = ROOT / "experiments" / "phase_03_freqai" / "results"
MODEL_DIR = ROOT / "freqtrade" / "user_data" / "freqai_models"

FEE = 0.001
MAX_OPEN = 3
START_WALLET = 100.0


def pair_file(pair: str) -> pathlib.Path:
    return DATA_DIR / (pair.replace("/", "_") + "-5m.feather")


def load_pair(pair: str, end=None) -> pd.DataFrame:
    df = pd.read_feather(pair_file(pair))
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)
    if end is not None:
        df = df[df["date"] <= pd.Timestamp(end)].reset_index(drop=True)
    return df


def featurize(df: pd.DataFrame) -> pd.DataFrame:
    """Feature+label+OHLC, tarih korunarak (index reset yok)."""
    feat = build_features(df)
    lab = build_labels(df)
    out = feat.join(lab)
    out["date"] = df["date"]
    for c in ["open", "high", "low", "close"]:
        out[c] = df[c].values
    return out.dropna().reset_index(drop=True)


def build_panel(pairs, end) -> dict:
    """pair -> featurize edilmis cerceve (end tarihine kadar veri)."""
    panel = {}
    for pair in pairs:
        df = load_pair(pair, end=end)
        if len(df) < 500:
            print(f"  [skip] {pair}: {len(df)} satir (yetersiz)", flush=True)
            continue
        panel[pair] = featurize(df)
    return panel


def pooled(panel: dict, start, end) -> pd.DataFrame:
    frames = []
    for pair, df in panel.items():
        s = slice_frame(df, start, end)
        assert_no_final_leak(s["date"], f"pool-{start}")
        if len(s):
            s = s.copy()
            s["pair"] = pair
            frames.append(s)
    if not frames:
        raise ValueError("bos pool")
    return pd.concat(frames, ignore_index=True)


def simulate(panel_signals: dict) -> tuple:
    """Global wallet, max 3 concurrent, stake=w*0.99/3. SL>ROI>sinyal önceliği.

    panel_signals: pair -> DataFrame[date, open, high, low, close, signal] (sıralı).
    Giris: sinyal mumu kapanışında. SL/ROI: aynı mumda SL önce (muhafazakar).
    """
    wallet = START_WALLET
    open_pos = {}
    trades = []
    idx = {p: {t: i for i, t in enumerate(df["date"])} for p, df in panel_signals.items()}
    all_ts = sorted(set().union(*[set(d["date"]) for d in panel_signals.values()]))
    for t in all_ts:
        for pair in sorted(open_pos):
            df = panel_signals[pair]
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
            elif row["signal"] == 0:
                px, reason = row["close"], "exit_signal"
            if px is not None:
                gross = (px - pos["entry"]) * pos["amount"]
                fee = pos["entry"] * pos["amount"] * FEE + px * pos["amount"] * FEE
                profit_abs = gross - fee
                trades.append({"pair": pair, "open_date": pos["entry_time"],
                               "close_date": t, "open_rate": pos["entry"],
                               "close_rate": px, "stake_amount": pos["stake"],
                               "profit_abs": profit_abs,
                               "profit_ratio": profit_abs / pos["stake"],
                               "exit_reason": reason})
                wallet += profit_abs
                del open_pos[pair]
        if len(open_pos) < MAX_OPEN:
            for pair in sorted(panel_signals):
                if len(open_pos) >= MAX_OPEN or pair in open_pos:
                    continue
                df = panel_signals[pair]
                i = idx[pair].get(t)
                if i is None or df.iloc[i]["signal"] != 1:
                    continue
                px = df.iloc[i]["close"]
                stake = wallet * 0.99 / MAX_OPEN
                open_pos[pair] = {"entry": px, "amount": stake / px,
                                  "stake": stake, "entry_time": t}
    for pair, pos in sorted(open_pos.items()):
        df = panel_signals[pair]
        px = df.iloc[-1]["close"]
        gross = (px - pos["entry"]) * pos["amount"]
        fee = pos["entry"] * pos["amount"] * FEE + px * pos["amount"] * FEE
        profit_abs = gross - fee
        trades.append({"pair": pair, "open_date": pos["entry_time"],
                       "close_date": df.iloc[-1]["date"], "open_rate": pos["entry"],
                       "close_rate": px, "stake_amount": pos["stake"],
                       "profit_abs": profit_abs,
                       "profit_ratio": profit_abs / pos["stake"],
                       "exit_reason": "force_exit"})
        wallet += profit_abs
    return trades, wallet


def metrics_from_trades(trades: list, win_start, win_end) -> dict:
    df = pd.DataFrame(trades)
    full_idx = pd.date_range(win_start, (pd.Timestamp(win_end) - pd.Timedelta(days=1)).date(),
                             freq="D").date
    if len(df) == 0:
        return {"trade_count": 0, "net_abs": 0.0, "daily_sharpe": 0.0,
                "sortino": 0.0, "max_dd": 0.0, "profit_factor": 0.0,
                "win_rate": 0.0, "turnover": 0, "total_volume": 0.0, "fee_est": 0.0}
    df["close_date"] = pd.to_datetime(df["close_date"])
    df["date"] = df["close_date"].dt.date
    daily_ratio = df.groupby("date")["profit_ratio"].sum()
    daily_full = pd.Series(0.0, index=full_idx)
    daily_full.update(daily_ratio)
    daily_abs = df.groupby("date")["profit_abs"].sum()
    abs_full = pd.Series(0.0, index=full_idx)
    abs_full.update(daily_abs)
    sh = sharpe(daily_full, periods_per_year=365)
    so = sortino(daily_full, periods_per_year=365)
    eq = START_WALLET + abs_full.cumsum()
    dd = float(((eq - eq.cummax()) / eq.cummax()).min())
    gw = df[df["profit_abs"] > 0]["profit_abs"].sum()
    gl = abs(df[df["profit_abs"] <= 0]["profit_abs"].sum())
    pf = float(gw / gl) if gl else float("inf")
    vol = float(df["stake_amount"].sum())
    return {"trade_count": len(df), "net_abs": round(float(df["profit_abs"].sum()), 3),
            "daily_sharpe": round(float(sh), 3),
            "sortino": round(float(so) if so != float("inf") else 0.0, 3),
            "max_dd": round(dd, 4), "profit_factor": round(pf, 3),
            "win_rate": round(float((df["profit_ratio"] > 0).mean()), 4),
            "turnover": len(df), "total_volume": round(vol, 1),
            "fee_est": round(vol * FEE * 2, 2)}


def run_seed(seed: int, panel: dict):
    t0 = time.time()
    train = pooled(panel, TRAIN_START, TRAIN_END)
    val = pooled(panel, VAL_START, VAL_END)
    Xtr, ytr = train[FEATURES].values, train["label"].values.astype(int)
    Xva = val[FEATURES].values
    print(f"[seed {seed}] train={len(Xtr)} (label1={ytr.mean():.3f}) val={len(Xva)}", flush=True)
    model = make_model(seed)
    model.fit(Xtr, ytr)
    try:
        import joblib
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_DIR / f"rf_seed{seed}.joblib")
    except Exception as e:
        print(f"  model kayit atlandi: {e}", flush=True)
    probas = predict_proba(model, Xva)
    val = val.copy()
    val["signal"] = [1 if p >= 0.5 else 0 for p in probas]
    sig = {}
    for pair, g in val.groupby("pair"):
        base = panel[pair][["date", "open", "high", "low", "close"]].copy()
        m = base.merge(g[["date", "signal"]], on="date", how="inner")
        sig[pair] = m.sort_values("date").reset_index(drop=True)
    trades, wallet = simulate(sig)
    met = metrics_from_trades(trades, VAL_START, VAL_END)
    met.update({"seed": seed, "n_train": len(Xtr), "n_val": len(Xva),
                "label_rate": round(float(ytr.mean()), 4),
                "fit_seconds": round(time.time() - t0, 1)})
    pd.DataFrame(trades).to_csv(RES_DIR / f"val_trades_seed{seed}.csv", index=False)
    print(f"[seed {seed}] trades={met['trade_count']} net={met['net_abs']} "
          f"sharpe={met['daily_sharpe']} dd={met['max_dd']} ({met['fit_seconds']}s)", flush=True)
    return met


def run_cv(panel: dict, seed: int = 42, only=None):
    folds = calendar_folds()
    rows = []
    for _, f in folds.iterrows():
        if only is not None and int(f["fold"]) not in only:
            continue
        tr = pooled(panel, f["train_start"], f["train_end"])
        te = pooled(panel, f["test_start"], f["test_end"])
        Xtr, ytr = tr[FEATURES].values, tr["label"].values.astype(int)
        model = make_model(seed)
        model.fit(Xtr, ytr)
        te = te.copy()
        te["signal"] = [1 if p >= 0.5 else 0 for p in predict_proba(model, te[FEATURES].values)]
        sig = {}
        for pair, g in te.groupby("pair"):
            base = panel[pair][["date", "open", "high", "low", "close"]].copy()
            m = base.merge(g[["date", "signal"]], on="date", how="inner")
            # test penceresi disi sizma: yalnizca fold araligi
            m = m[(m["date"] >= pd.Timestamp(f["test_start"])) &
                  (m["date"] <= pd.Timestamp(f["test_end"]) - pd.Timedelta(hours=1))]
            sig[pair] = m.sort_values("date").reset_index(drop=True)
        trades, _ = simulate(sig)
        met = metrics_from_trades(trades, f["test_start"], f["test_end"])
        met.update({"fold": int(f["fold"]), "seed": seed, "n_train": len(Xtr)})
        rows.append(met)
        pd.DataFrame(trades).to_csv(RES_DIR / f"cv_trades_fold{int(f['fold'])}_seed{seed}.csv",
                                    index=False)
        print(f"[cv fold {int(f['fold'])}] trades={met['trade_count']} "
              f"net={met['net_abs']} sharpe={met['daily_sharpe']}", flush=True)
    out = RES_DIR / "cv_metrics.csv"
    new = pd.DataFrame(rows)
    if out.exists() and len(new):
        old = pd.read_csv(out)
        old = old[~old["fold"].isin(new["fold"])]
        new = pd.concat([old, new], ignore_index=True)
    if len(new):
        new.sort_values("fold").to_csv(out, index=False)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", nargs="*", type=int, default=[])
    ap.add_argument("--cv", action="store_true")
    ap.add_argument("--cv-folds", nargs="*", type=int, default=None)
    args = ap.parse_args()
    RES_DIR.mkdir(parents=True, exist_ok=True)
    # Final A'ya dokunma: panel VAL sonuyla sinirli
    panel = build_panel(ELIGIBLE_18, end=VAL_END)
    print(f"panel: {len(panel)} pair", flush=True)
    if args.seeds:
        rows = []
        for s in args.seeds:
            if s not in SEEDS:
                raise SystemExit(f"kilitli seed disi: {s}")
            rows.append(run_seed(s, panel))
        out = RES_DIR / "val_metrics.csv"
        old = pd.read_csv(out) if out.exists() else pd.DataFrame()
        new = pd.DataFrame(rows)
        if len(old):
            old = old[~old["seed"].isin(new["seed"])]
            new = pd.concat([old, new], ignore_index=True)
        new.sort_values("seed").to_csv(out, index=False)
        print(f"yazildi: {out}", flush=True)
    if args.cv or args.cv_folds is not None:
        run_cv(panel, only=args.cv_folds)
        print("yazildi: cv_metrics.csv", flush=True)


if __name__ == "__main__":
    main()
