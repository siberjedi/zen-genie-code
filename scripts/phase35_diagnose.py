"""Phase 3.5 diagnosis — SALT-OKUNUR teşhis (2026-09-04).

YASAKLAR: eğitim yok, tuning yok, Final Test A yok (okuma bile yok),
backtest yok, düzeltme yok, threshold/değişiklik yok.
SERBEST: dondurulmuş modelle inference (validation), mevcut CSV/zip/feather okuma.

Çıktı: experiments/phase_03_freqai/diagnosis/ (küçük CSV'ler) + stdout özeti.
"""
import pathlib
import sys
import zipfile
import json

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from scripts.phase03_experiment import build_panel, ELIGIBLE_18, MODEL_DIR, FEE
from src.freqai.features import FEATURES
from src.freqai.labels import LABEL_HORIZON, LABEL_THRESHOLD, build_labels
from src.freqai.splits import (slice_frame, VAL_START, VAL_END, FINAL_A_START,
                               assert_no_final_leak)
from src.freqai.model import predict_proba

OUT = ROOT / "experiments" / "phase_03_freqai" / "diagnosis"
OUT.mkdir(parents=True, exist_ok=True)
SEED = 2026  # SELECTION.md ile seçilmiş seed (değişiklik değil, tekrar kullanım)


def main():
    # ---- 1. dondurulmuş model + validation paneli (VAL_END kesikli: Final A YOK) ----
    model = joblib.load(MODEL_DIR / f"rf_seed{SEED}.joblib")
    panel = build_panel(ELIGIBLE_18, end=VAL_END)
    frames = []
    for pair, df in panel.items():
        s = slice_frame(df, VAL_START, VAL_END).copy()
        assert_no_final_leak(s["date"], f"diag-{pair}")
        assert (s["date"] < FINAL_A_START).all()
        s["pair"] = pair
        frames.append(s)
    val = pd.concat(frames, ignore_index=True)
    X = val[FEATURES].values
    proba = np.array(predict_proba(model, X))
    val["proba"] = proba
    val["signal"] = (proba >= 0.5).astype(int)
    print(f"val satir: {len(val)}, pair: {val['pair'].nunique()}", flush=True)

    # ---- 2. churn ----
    flips, runs, stays = {}, [], {1: [], 3: [], 6: [], 12: []}
    unnec = 0
    for pair, g in val.groupby("pair"):
        s = g.sort_values("date")["signal"].values
        flips[pair] = int(np.abs(np.diff(s)).sum())
        # run-length
        ch = np.concatenate([[True], s[1:] != s[:-1]])
        ids = np.cumsum(ch)
        for _, grp in pd.Series(s).groupby(ids):
            runs.append(len(grp))
        for k in stays:
            stays[k].append(float((s[k:] == s[:-k]).mean()) if len(s) > k else np.nan)
        # gereksiz flip: izole tek mum (010 veya 101)
        unnec += int((((s[:-2] == s[2:]) & (s[1:-1] != s[:-2])).sum()))
    runs = np.array(runs)
    print(f"CHURN flips={sum(flips.values())} pairs={len(flips)} "
          f"avg_flip/pair={np.mean(list(flips.values())):.0f}", flush=True)
    print(f"RUN med={np.median(runs):.0f} mean={runs.mean():.1f} "
          f"P25={np.percentile(runs,25):.0f} P75={np.percentile(runs,75):.0f} "
          f"P90={np.percentile(runs,90):.0f} P95={np.percentile(runs,95):.0f}", flush=True)
    for k, v in stays.items():
        print(f"STAY {k*5}dk: {np.nanmean(v):.3f}", flush=True)
    total_sig = len(val)
    print(f"UNNEC isolated flips: {unnec} ({unnec/total_sig*100:.1f}% tum sinyallerin)", flush=True)
    pd.DataFrame({"pair": list(flips.keys()),
                  "flips": list(flips.values())}).to_csv(OUT / "churn_by_pair.csv", index=False)

    # ---- 3. proba dağılımı + AUC/kalibrasyon (kilitli label'a karşı) ----
    hist, edges = np.histogram(proba, bins=20, range=(0, 1))
    pd.DataFrame({"bin_lo": edges[:-1], "bin_hi": edges[1:], "count": hist}).to_csv(
        OUT / "proba_hist.csv", index=False)
    gray = ((proba >= 0.45) & (proba <= 0.55)).mean()
    print(f"PROBA mean={proba.mean():.3f} std={proba.std():.3f} "
          f"gray[0.45-0.55]={gray*100:.1f}% min={proba.min():.3f} max={proba.max():.3f}", flush=True)
    auc = roc_auc_score(val["label"].values.astype(int), proba)
    print(f"AUC vs locked label: {auc:.4f}", flush=True)
    cal = val.assign(bin=pd.cut(val["proba"], bins=10)).groupby(
        "bin", observed=True).agg(n=("label", "size"), rate=("label", "mean"),
                                  pmean=("proba", "mean"))
    cal.to_csv(OUT / "calibration.csv")
    print("CALIBRATION:\n" + cal.to_string(), flush=True)

    # ---- 4. label economics (validation penceresi) ----
    fwd = {}
    for pair, df in panel.items():
        d = df[(df["date"] >= pd.Timestamp(VAL_START)) &
               (df["date"] <= pd.Timestamp(VAL_END) - pd.Timedelta(hours=1))].copy()
        c = d["close"].values
        r12 = c[LABEL_HORIZON:] / c[:-LABEL_HORIZON] - 1
        fwd[pair] = r12
    allr = np.concatenate(list(fwd.values()))
    pos = allr[allr > LABEL_THRESHOLD]
    print(f"LABEL rate={len(pos)/len(allr):.3f} fwd mean={allr.mean():.5f} std={allr.std():.5f}", flush=True)
    print(f"FWD pct: 5={np.percentile(allr,5)*100:.2f}% 25={np.percentile(allr,25)*100:.2f}% "
          f"50={np.percentile(allr,50)*100:.3f}% 75={np.percentile(allr,75)*100:.2f}% "
          f"95={np.percentile(allr,95)*100:.2f}%", flush=True)
    print(f"P(fwd>thr)={len(pos)/len(allr):.3f} P(fwd>2xthr)={(allr>2*LABEL_THRESHOLD).mean():.3f} "
          f"P(fwd>4xthr)={(allr>4*LABEL_THRESHOLD).mean():.3f}", flush=True)
    print(f"E[fwd|label=1]={pos.mean()*100:.3f}% fee sonrası={pos.mean()*100-0.2:.3f}% "
          f"(fee=0.2% round-trip)", flush=True)
    pd.DataFrame({"stat": ["n", "label_rate", "fwd_mean", "fwd_std", "p_gt_thr",
                           "p_gt_2thr", "mean_pos", "mean_pos_net_fee"],
                  "value": [len(allr), len(pos)/len(allr), allr.mean(), allr.std(),
                            (allr > LABEL_THRESHOLD).mean(),
                            (allr > 2*LABEL_THRESHOLD).mean(), pos.mean(),
                            pos.mean() - 2*FEE]}).to_csv(OUT / "label_economics.csv", index=False)

    # ---- 5+6. cost + holding (mevcut val trades) ----
    t = pd.read_csv(ROOT / "experiments/phase_03_freqai/results/val_trades_seed2026.csv")
    t["amount"] = t["stake_amount"] / t["open_rate"]
    t["fee_in"] = t["open_rate"] * t["amount"] * FEE
    t["fee_out"] = t["close_rate"] * t["amount"] * FEE
    t["fee"] = t["fee_in"] + t["fee_out"]
    t["gross"] = t["profit_abs"] + t["fee"]
    gw, gl = t[t.gross > 0].gross.sum(), t[t.gross <= 0].gross.sum()
    print(f"COST gross+={gw:.1f} gross-={gl:.1f} fee={t.fee.sum():.1f} "
          f"net={t.profit_abs.sum():.1f} (kontrol: {gw+gl-t.fee.sum():.1f})", flush=True)
    print(f"PER-TRADE gross={t.gross.mean():.4f} fee={t.fee.mean():.4f} "
          f"net={t.profit_abs.mean():.4f} (fee/gross_edge={t.fee.mean()/abs(t.gross.mean()):.1f}x)", flush=True)
    t["open_date"] = pd.to_datetime(t["open_date"])
    t["close_date"] = pd.to_datetime(t["close_date"])
    t["hold_min"] = (t["close_date"] - t["open_date"]).dt.total_seconds() / 60
    h = t["hold_min"]
    print(f"HOLD med={h.median():.0f} mean={h.mean():.0f} "
          f"P25={h.quantile(.25):.0f} P75={h.quantile(.75):.0f} "
          f"P90={h.quantile(.90):.0f} P95={h.quantile(.95):.0f}", flush=True)
    t["bucket"] = pd.cut(h, [0, 5, 15, 60, 1e9],
                         labels=["<=5m", "5-15m", "15-60m", ">60m"])
    gb = t.groupby("bucket", observed=True).agg(n=("profit_abs", "size"),
                                                gross=("gross", "sum"),
                                                net=("profit_abs", "sum"),
                                                wr=("profit_abs", lambda s: (s > 0).mean()))
    gb.to_csv(OUT / "holding_buckets.csv")
    print("HOLD-BUCKETS:\n" + gb.round(2).to_string(), flush=True)
    print(f"HOLD-NET corr: {t[['hold_min','profit_abs']].corr().iloc[0,1]:.3f}", flush=True)

    # ---- 7. baseline val karsilastirma (mevcut zip, yeni backtest YOK) ----
    z = zipfile.ZipFile(ROOT / "freqtrade/user_data/backtest_results/phase03/backtest-result-2026-09-04_12-13-08.zip")
    n = [x for x in z.namelist() if x.endswith(".json") and "config" not in x][0]
    b = pd.DataFrame(json.loads(z.read(n))["strategy"]["BaselineStrategy"]["trades"])
    b["amount"] = b["stake_amount"] / b["open_rate"]
    b["fee"] = (b["open_rate"] * b["amount"] + b["close_rate"] * b["amount"]) * FEE
    b["gross"] = b["profit_abs"] + b["fee"]
    bgw, bgl = b[b.gross > 0].gross.sum(), b[b.gross <= 0].gross.sum()
    b["open_date"] = pd.to_datetime(b["open_date"])
    b["close_date"] = pd.to_datetime(b["close_date"])
    bh = (b["close_date"] - b["open_date"]).dt.total_seconds() / 60
    print(f"BASELINE n={len(b)} gross+={bgw:.1f} gross-={bgl:.1f} fee={b['fee'].sum():.1f} "
          f"net={b['profit_abs'].sum():.1f} per-trade gross={b['gross'].mean():.4f} "
          f"fee={b['fee'].mean():.4f}", flush=True)
    print(f"BASELINE hold med={bh.median():.0f} mean={bh.mean():.0f} "
          f"turnover/gun={len(b)/180:.1f} vs freqai {len(t)/180:.1f}", flush=True)
    print(f"BASELINE exits: {b['exit_reason'].value_counts().to_dict()}", flush=True)
    pd.DataFrame({"side": ["freqai", "baseline"],
                  "n": [len(t), len(b)],
                  "gross": [t.gross.sum(), b.gross.sum()],
                  "fee": [t.fee.sum(), b['fee'].sum()],
                  "net": [t.profit_abs.sum(), b.profit_abs.sum()],
                  "per_trade_gross": [t.gross.mean(), b.gross.mean()],
                  "per_trade_fee": [t.fee.mean(), b['fee'].mean()],
                  "med_hold_min": [t.hold_min.median(), bh.median()]}).to_csv(
        OUT / "cost_compare.csv", index=False)

    # ---- 8. implementation trace (mevcut trades, kod degisikligi YOK) ----
    issues = []
    # 8a. pair-ici overlap
    ov = 0
    for pair, g in t.groupby("pair"):
        g = g.sort_values("open_date").reset_index(drop=True)
        if ((g["open_date"].values[1:] < g["close_date"].values[:-1]).any()):
            ov += 1
    issues.append(f"pair-ici overlap: {ov} pair")
    # 8b. force_exit konumu
    fe = t[t.exit_reason == "force_exit"]
    issues.append(f"force_exit: {len(fe)} (pencere sonu disi: "
                  f"{(pd.to_datetime(fe['close_date']) < pd.Timestamp(VAL_END) - pd.Timedelta(days=1)).sum()})")
    # 8c. duplicate (pair, open_date)
    issues.append(f"duplicate (pair,open): {t.duplicated(['pair','open_date']).sum()}")
    # 8d. pencere disi trade
    issues.append(f"open<VAL_START: {(t.open_date < str(VAL_START)).sum()}, "
                  f"close>VAL_END: {(t.close_date > str(VAL_END)).sum()}")
    # 8e. fee formül spot check (ilk 3 trade, feather close ile)
    print("TRACE: " + " | ".join(issues), flush=True)
    with open(OUT / "trace_checks.txt", "w") as f:
        f.write("\n".join(issues) + "\n")
    print("yazildi: diagnosis/ (churn, proba, calibration, label, holding, cost, trace)", flush=True)


if __name__ == "__main__":
    main()
