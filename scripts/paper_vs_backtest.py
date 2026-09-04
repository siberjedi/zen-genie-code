"""
Faz 10 — Backtest vs Live Paper gap raporu.
Özellikle haber anındaki spread/likidite/latency/slippage.
"""
import pandas as pd, json, pathlib

def compare(backtest_csv, paper_csv):
    bt=pd.read_csv(backtest_csv) if pathlib.Path(backtest_csv).exists() else pd.DataFrame()
    pp=pd.read_csv(paper_csv) if pathlib.Path(paper_csv).exists() else pd.DataFrame()
    print(f"backtest trades: {len(bt)}, paper trades: {len(pp)}")
    if bt.empty or pp.empty:
        print("veri yok — Faz 10 henüz koşmadı")
        return
    for col in ["profit_ratio"]:
        if col in bt and col in pp:
            gap = pp[col].mean() - bt[col].mean()
            print(f"{col} gap (paper - backtest): {gap:.4f}")

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--bt", default="experiments/phase_02_walkforward/trades.csv")
    p.add_argument("--paper", default="experiments/phase_10_paper/trades.csv")
    args=p.parse_args()
    compare(args.bt, args.paper)
