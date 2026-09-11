"""Phase 10 BACKTEST — frozen kurallar (E1/E2/E3), saf muhasebe.

Getiri HESABI (ilk kez): event gross -> net(C=0.003) -> metrikler.
Tuning/rescue YOK. FDR-3 (BH, tek-yonlu t-test netler uzerinde).
Overlap analizi BETIMSEL (yeni test YOK).
Karar: kural-bazinda gate zinciri; tum FAIL -> Phase 10 kapat;
  PASS -> candidate-only (tuning/gercek-para YOK).

Calistir: py -3 scripts/phase10_backtest.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase502_labels import load_dataset_slice
from src.timeconv import to_ms

D10 = ROOT / "experiments" / "phase_10_calendar" / "data"
R10 = ROOT / "experiments" / "phase_10_calendar" / "results10"
COST = 0.003
DIRS = {"E1": 1.0, "E2": 1.0, "E3": -1.0}  # kilitli yonler
ALPHA = 0.05


def week_block_ci(r, weeks, n_boot=10000, seed=42, lam=None):
    """Takvim-haftasi blok-bootstrap (haftalar Mon-Sun; mevsimsellik korunur)."""
    rng = np.random.default_rng(seed)
    r = np.asarray(r, float)
    uw = np.unique(weeks)
    byw = [np.where(weeks == w)[0] for w in uw]
    n = len(r)
    outs = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(byw), len(byw))
        idx = np.concatenate([byw[i] for i in pick])[:n]
        if len(idx) < n:  # kuyruk doldurma (deterministik sarmalama)
            idx = np.concatenate([idx, np.arange(n - len(idx))])
        sm = r[idx]
        outs[b] = sm.mean() / sm.std(ddof=1) * np.sqrt(lam) if sm.std(ddof=1) > 0 else np.nan
    lo, hi = np.nanpercentile(outs, [2.5, 97.5])
    mu, sd = r.mean(), r.std(ddof=1)
    return float(mu / sd * np.sqrt(lam)), float(lo), float(hi)


def main():
    R10.mkdir(parents=True, exist_ok=True)
    from scipy import stats as st
    from statsmodels.stats.power import TTestPower
    pw = TTestPower()
    spot = load_dataset_slice()[["date", "close"]]
    ts = pd.to_datetime(spot["date"])
    ts = ts.dt.tz_localize("UTC") if getattr(ts.dt, "tz", None) is None else ts
    px = dict(zip(to_ms(ts),
                   spot["close"].to_numpy(float)))
    ev = pd.read_parquet(D10 / "events10.parquet")
    out = {"rules": {}}
    lam_base = 365.0 / 1277.0
    all_nets = {}
    for rule in ("E1", "E2", "E3"):
        sub = ev[ev["rule"] == rule].reset_index(drop=True)
        en = to_ms(sub["entry"])
        ex = to_ms(sub["exit"])
        assert all(x in px and y in px for x, y in zip(en, ex)), f"STOP: {rule} bar eksik"
        c_in = np.array([px[x] for x in en])
        c_out = np.array([px[y] for y in ex])
        gross = DIRS[rule] * (c_out / c_in - 1.0)
        net = gross - COST
        n = len(net)
        lam = n * lam_base
        wk = pd.to_datetime(sub["entry"]).dt.isocalendar()
        weeks = (wk["year"].astype(str) + "-W" + wk["week"].astype(str)).to_numpy()
        theta, lo, hi = week_block_ci(net, weeks, lam=lam)
        eq = np.cumsum(net)
        maxdd = float(-(eq - np.maximum.accumulate(eq)).min())
        d = float(net.mean() / net.std(ddof=1)) if net.std(ddof=1) > 0 else 0.0
        tstat, pval = (st.ttest_1samp(net, 0.0, alternative="greater")
                       if net.std(ddof=1) > 0 else (0.0, 1.0))
        power = float(pw.power(effect_size=abs(d), nobs=n, alpha=ALPHA, alternative="larger"))
        edge = float(net.mean() / COST)
        out["rules"][rule] = {
            "n": n, "gross": round(float(net.mean() + COST), 6),
            "cost": COST, "net": round(float(net.mean()), 6),
            "edge": round(edge, 3), "theta": round(theta, 4),
            "ci95": [round(lo, 4), round(hi, 4)],
            "maxdd": round(maxdd, 4),
            "win_rate": round(float((net > 0).mean()), 4),
            "turnover_per_year": round(n * 365.0 / 1277.0, 1),
            "d": round(d, 4), "power": round(power, 3),
            "t": round(float(tstat), 3), "p": float(pval),
            "mean_hold_bars": {"E1": 576, "E2": 96, "E3": 36}[rule],
        }
        all_nets[rule] = net
        print(f"  {rule}: n={n} net={net.mean():+.6f} edge={edge:.3f} "
              f"theta={theta:+.3f} CI=[{lo:+.3f},{hi:+.3f}] maxdd={maxdd:.4f} "
              f"p={pval:.4f}", flush=True)
    # FDR-3 (BH, tek-yonlu t p-degerleri)
    ps = [out["rules"][r]["p"] for r in ("E1", "E2", "E3")]
    order = np.argsort(ps)
    qs = np.empty(3)
    run = 1.0
    for pos in range(2, -1, -1):
        i = order[pos]
        run = min(run, ps[i] * 3 / (pos + 1))
        qs[i] = run
    for r, q in zip(("E1", "E2", "E3"), qs):
        out["rules"][r]["q"] = round(float(q), 4)
    print(f"  FDR q: E1={qs[0]:.4f} E2={qs[1]:.4f} E3={qs[2]:.4f}", flush=True)
    # gate zinciri (kural-bazinda; AUC/IC/tau YOK — skor yok)
    cands = []
    for r in ("E1", "E2", "E3"):
        m = out["rules"][r]
        g = {"net_pos": bool(m["net"] > 0), "edge": bool(m["edge"] >= 1.2),
             "theta_ci": bool(m["ci95"][0] > 0), "maxdd": bool(m["maxdd"] <= 0.20),
             "d_power": bool(abs(m["d"]) >= 0.30 and m["power"] >= 0.80),
             "fdr": bool(m["q"] < ALPHA)}
        g["chain"] = all(g.values())
        m["gates"] = g
        if g["chain"]:
            cands.append(r)
        print(f"  {r} gates={g}", flush=True)
    # E1nE2 overlap (BETIMSEL, test YOK)
    e1 = ev[ev["rule"] == "E1"][["entry", "exit"]].to_numpy()
    e2 = ev[ev["rule"] == "E2"][["entry", "exit"]].to_numpy()
    e1s = sorted((pd.Timestamp(a).value, pd.Timestamp(b).value) for a, b in e1)
    inside, outside = [], []
    net2 = all_nets["E2"]
    for k, (a, b) in enumerate(e2):
        t = pd.Timestamp(a).value
        (inside if any(x <= t < y for x, y in e1s) else outside).append(net2[k])
    inside, outside = np.array(inside), np.array(outside)
    out["overlap_E1nE2"] = {
        "E2_inside_E1": {"n": int(len(inside)), "mean_net": round(float(inside.mean()), 6)} if len(inside) else {},
        "E2_outside_E1": {"n": int(len(outside)), "mean_net": round(float(outside.mean()), 6)} if len(outside) else {},
        "note": "betimsel; test YOK (FDR-disi); kollar bagimsiz (netting yok)",
    }
    print(f"  overlap: inside n={len(inside)} mean={inside.mean() if len(inside) else '-':+.6f} | "
          f"outside n={len(outside)} mean={outside.mean() if len(outside) else '-':+.6f}", flush=True)
    out["candidates"] = cands
    out["decision"] = "CLOSE" if not cands else "CANDIDATE"
    with open(R10 / "RESULTS_10.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    with open(R10 / "GATE_10.json", "w", encoding="utf-8") as f:
        json.dump({r: out["rules"][r]["gates"] for r in ("E1", "E2", "E3")},
                  f, indent=2, default=str)
    rows = []
    for r in ("E1", "E2", "E3"):
        sub = ev[ev["rule"] == r].reset_index(drop=True)
        rows.append(pd.DataFrame({"rule": r, "entry": pd.to_datetime(sub["entry"]),
                                  "exit": pd.to_datetime(sub["exit"]),
                                  "net": all_nets[r]}))
    pd.concat(rows, ignore_index=True).to_parquet(R10 / "oof10.parquet")
    md = ["# PHASE 10 — RESULTS (frozen kurallar, backtest)"]
    md.append("")
    for r in ("E1", "E2", "E3"):
        m = out["rules"][r]
        md.append(f"## {r}: n={m['n']} gross={m['gross']:+.6f} cost={m['cost']} "
                  f"net={m['net']:+.6f} edge={m['edge']:.3f} theta={m['theta']:+.3f} "
                  f"CI={m['ci95']} maxdd={m['maxdd']} win={m['win_rate']} "
                  f"turnover/yr={m['turnover_per_year']} d={m['d']:+.3f} "
                  f"power={m['power']:.2f} p={m['p']:.4f} q={m['q']:.4f} gates={m['gates']}")
    md.append("")
    md.append(f"## FDR-3: E1={qs[0]:.4f} E2={qs[1]:.4f} E3={qs[2]:.4f}")
    md.append(f"## Overlap E1nE2: {out['overlap_E1nE2']}")
    md.append(f"## Karar: {out['decision']} {cands}")
    md.append("")
    md.append("**READY FOR USER DECISION**" if cands else "**PHASE 10 CLOSED**")
    with open(ROOT / "experiments/phase_10_calendar/PHASE_10_RESULTS.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Karar: {out['decision']} {cands}", flush=True)


if __name__ == "__main__":
    main()