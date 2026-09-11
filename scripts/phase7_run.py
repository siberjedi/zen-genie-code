"""Phase 7 — H48 fresh deterministic run (LOCKED DESIGN_700).

Tek primary kol: BASE-7 = B3 / L1@H48 / M2 / seed42. 5m grid.
Execution: frozen TRAIN-q90 esigi; 48-bar hold; r_i = Y_i(48) - C.
Primary: yillik net per-trade Sharpe, event-block bootstrap CI (K=500, 10k, s42).
Karsilastirici: E032-verbatim H12 refit -> theta_12 (betimsel) + PSS tutarlilik.
Gate'ler DESIGN_700 §9 aynen. H72 YOK. Tuning YOK. Protected kapali.

Calistir: py -3 scripts/phase7_run.py (arka planda + log)
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase501_features import BLOCKS
from phase502_labels import build_frame, COST_C, TF_MINUTES
from phase503_models import make_model, fit_predict, M2
from phase504_walkforward import (phase5_folds, bounds_respected, run_fold,
                                  wf_pss_scores, wf_consistency, overlap_report,
                                  WF_MIN_CONSISTENCY)
from phase505_stats import (cell_metrics, pss_stats, benjamini_hochberg, ALPHA,
                            power_of)
from phase6a_run import split_arm, wf_slice
from src.freqai.p5_splits import VAL_START, VAL_END
from src.timeconv import to_ms

A7 = ROOT / "experiments" / "phase_07_horizon"
RES7 = A7 / "results7"
H = 48
SEED = 42
N_BOOT = 10000
BOOT_K = 500
CPU_CAP = 12.0
LEDGER = []
E032_REF = -0.002116745525
VAL_DAYS = 181


def fit_scores(Xtr, ytr, Xv, model_id=M2, label="L1", seed=SEED):
    t0 = time.process_time()
    est, _ = make_model(model_id, label, seed)
    sc, _, _ = fit_predict(est, None, Xtr, ytr, Xv)
    return sc, round(time.process_time() - t0, 1)


def theta_from_events(r, lam):
    r = np.asarray(r, float)
    mu, sd = r.mean(), r.std(ddof=1)
    return float(mu / sd * np.sqrt(lam)) if sd > 0 and len(r) > 1 else 0.0


def block_bootstrap_theta(r, K=BOOT_K, n_boot=N_BOOT, seed=SEED, lam=None):
    """Giris-sirali event serisinde moving-block bootstrap (K event).
    lam dondurulmus olcek sabiti. Donus: (mean_theta, lo, hi)."""
    rng = np.random.default_rng(seed)
    r = np.asarray(r, float)
    n = len(r)
    assert n >= K, f"STOP: yetersiz event (n={n} < K={K})"
    nblocks = int(np.ceil(n / K))
    outs = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n - K + 1, nblocks)
        idx = np.concatenate([np.arange(s, s + K) for s in starts])[:n]
        samp = r[idx]
        mu, sd = samp.mean(), samp.std(ddof=1)
        outs[b] = mu / sd * np.sqrt(lam) if sd > 0 else np.nan
    lo, hi = np.nanpercentile(outs, [2.5, 97.5])
    return float(np.nanmean(outs)), float(lo), float(hi)


def event_metrics(r, lam, label=""):
    r = np.asarray(r, float)
    n = len(r)
    theta = theta_from_events(r, lam)
    _, lo, hi = block_bootstrap_theta(r, lam=lam)
    eq = np.cumsum(r)
    dd = eq - np.maximum.accumulate(eq)
    maxdd = float(-dd.min()) if n else 0.0
    downside = r[r < 0]
    sortino = float(r.mean() / downside.std(ddof=1) * np.sqrt(lam)) if len(downside) > 1 and downside.std(ddof=1) > 0 else 0.0
    gains = r[r > 0].sum()
    losses = -r[r < 0].sum()
    return {"n": n, "theta": round(theta, 4), "ci95": [round(lo, 4), round(hi, 4)],
            "mean_net": float(r.mean()), "gross": float(r.mean() + COST_C),
            "maxdd": round(maxdd, 4), "sortino": round(sortino, 4),
            "profit_factor": round(float(gains / losses), 4) if losses > 0 else float("inf"),
            "win_rate": round(float((r > 0).mean()), 4)}


def main():
    t_start = time.time()
    RES7.mkdir(parents=True, exist_ok=True)
    print("== PHASE 7 RUN (BASE-7 H48 M2 s42; theta12 comparator) ==", flush=True)

    f48 = build_frame(tf_minutes=5, horizon=H)
    f12 = build_frame(tf_minutes=5, horizon=12)
    assert len(f48) == len(f12), "grid uyumsuz"
    assert (to_ms(f48["date"])
            == to_ms(f12["date"])).all(), "grid kaydi"
    b3 = BLOCKS["B3"]

    # --- H48 kolu ---
    d = split_arm(f48, b3, label="L1", horizon=H)
    sc, cpu = fit_scores(d["X_train"], d["y_train"], d["X_val"])
    LEDGER.append({"arm": "BASE7-H48", "cpu_sec": cpu})
    # determinizm self-check (tol 1e-9, STOP)
    sc2, cpu2 = fit_scores(d["X_train"], d["y_train"], d["X_val"])
    LEDGER.append({"arm": "BASE7-H48-determinism", "cpu_sec": cpu2})
    dd = float(np.max(np.abs(sc - sc2)))
    print(f"  determinism diff={dd:.2e}", flush=True)
    if dd >= 1e-9:
        raise RuntimeError(f"STOP: reproducibility failure (diff={dd:.2e})")
    met = cell_metrics(sc, d["y_val"], d["y_future_val"], "L1", "B3", M2,
                       cost=COST_C, seed=SEED, cell_id="H48")
    met["n_train"] = d["n_train"]
    print(f"  H48: n_tr={d['n_train']} n_val={d['n_val']} pss={met['pss']['pss']:+.6f} "
          f"edge={met['pss']['edge_over_cost']:.3f} auc={met['auc']:.4f} "
          f"ic={met['rank_ic']:.4f} cpu={cpu}s", flush=True)

    # frozen TRAIN-q90 esigi (TRAIN skorlarindan; VAL-pooled YOK)
    q90 = float(np.quantile(_train_scores(d), 0.90))
    print(f"  q90_TRAIN={q90:.6f}", flush=True)
    ev_mask = sc >= q90
    r = d["y_future_val"][ev_mask] - COST_C
    lam = len(r) * 365.0 / VAL_DAYS
    em = event_metrics(r, lam)
    print(f"  events={em['n']} (rate={em['n']/len(sc):.3f}) theta={em['theta']:+.4f} "
          f"CI95={em['ci95']} maxdd={em['maxdd']}", flush=True)

    # --- theta_12 karsilastirici (E032-verbatim refit, betimsel) ---
    d12 = split_arm(f12, b3, label="L1", horizon=12)
    sc12, cpu12 = fit_scores(d12["X_train"], d12["y_train"], d12["X_val"])
    LEDGER.append({"arm": "BASE-H12-refit", "cpu_sec": cpu12})
    m12 = cell_metrics(sc12, d12["y_val"], d12["y_future_val"], "L1", "B3", M2,
                       cost=COST_C, seed=SEED, cell_id="H12")
    pdiff = abs(m12["pss"]["pss"] - E032_REF)
    print(f"  E032 PSS tutarlilik: diff={pdiff:.2e}", flush=True)
    if pdiff >= 1e-9:
        raise RuntimeError(f"STOP: E032 consistency failure (diff={pdiff:.2e})")
    q90_12 = float(np.quantile(_train_scores(d12), 0.90))
    r12 = d12["y_future_val"][sc12 >= q90_12] - COST_C
    lam12 = len(r12) * 365.0 / VAL_DAYS
    em12 = event_metrics(r12, lam12)
    print(f"  theta12: events={em12['n']} theta={em12['theta']:+.4f} CI95={em12['ci95']}", flush=True)

    # --- gate zinciri (H48) ---
    p = met["pss"]
    gates = {
        "a_pss_edge": bool(p["pss_positive"] and p["edge_ge_1.2"]),
        "b_support": bool(met["auc"] >= 0.55 and met["rank_ic"] >= 0.01 and met["kendall_tau"] > 0),
        "c_theta": bool(em["ci95"][0] > 0),
        "d_effect": bool(p["cohens_d"] >= 0.30 and p["power"] >= 0.80),
        "e_fdr": bool(p["p_test"] < ALPHA),
        "f_maxdd": bool(em["maxdd"] <= 0.20),
    }
    gates["chain_no_wf_seed"] = all(gates.values())
    print(f"  GATES(primary) {gates}", flush=True)

    extra = {"theta12": em12, "q90_train_H48": q90, "q90_train_H12": q90_12}
    # turnover diagnostic (preregistered, gatesiz)
    entry_idx = np.where(ev_mask)[0]
    extra["turnover"] = {"events_per_year": round(len(r) * 365.0 / VAL_DAYS, 1),
                         "event_rate": round(float(ev_mask.mean()), 4)}
    decision = "FAIL"
    if gates["chain_no_wf_seed"]:
        seed_pss = {}
        for sd in (42, 7, 123):
            scc, cpuc = fit_scores(d["X_train"], d["y_train"], d["X_val"], seed=sd)
            LEDGER.append({"arm": f"H48-seed{sd}", "cpu_sec": cpuc})
            sm = cell_metrics(scc, d["y_val"], d["y_future_val"], "L1", "B3", M2,
                              cost=COST_C, seed=sd, cell_id=f"H48-s{sd}")
            seed_pss[str(sd)] = sm["pss"]["pss"]
        signs = [1 if v > 0 else 0 for v in seed_pss.values()]
        extra["seed_consistency"] = {"frac": sum(signs) / len(signs),
                                     "pass": sum(signs) / len(signs) >= 2 / 3}
        folds = phase5_folds()
        bounds_respected(folds)
        fres = []
        for i, fo in enumerate(folds):
            fs = wf_slice(fo, f48, b3, horizon=H)
            scc = run_fold(fs, M2, "L1", seed=SEED)
            pv, nt, m10, netp = wf_pss_scores(scc, fs["y_future_val"], COST_C)
            fres.append({"fold": i, "pss": pv, "n_val": fs["n_val"],
                         "net_positive": netp, "n_top": nt, "mean10": m10})
        cons = wf_consistency(fres, p["pss"] > 0)
        extra["wf"] = {"consistency": round(cons, 4),
                       "pass_ge_0.60": bool(cons >= WF_MIN_CONSISTENCY),
                       "folds": fres, "overlap": overlap_report(folds)}
        g_seed = extra["seed_consistency"]["pass"]
        g_wf = extra["wf"]["pass_ge_0.60"]
        decision = "PASS" if (g_seed and g_wf) else "FAIL"
        print(f"  seed={extra['seed_consistency']} wf={cons:.3f} -> {decision}", flush=True)

    verdict = {"PASS": "PASS — H48 REPLICATION CANDIDATE",
               "FAIL": "FAIL — H48 ECONOMIC EDGE YOK",
               "STOP": "STOP — EXPERIMENT INVALID"}[decision]
    total_cpu = sum(x["cpu_sec"] for x in LEDGER)
    budget = {"cpu_hours": round(total_cpu / 3600, 4), "within": total_cpu < CPU_CAP * 3600,
              "ledger": LEDGER}
    out = {"cell": met, "events": em, "delta_theta_vs_H12": round(em["theta"] - em12["theta"], 4),
           "gates": gates, "decision": decision, "verdict": verdict,
           "extra": extra, "budget": budget, "lock": "DESIGN_700", "H": H, "seed": SEED}
    with open(RES7 / "RESULTS_7.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    with open(RES7 / "METRICS_7.json", "w", encoding="utf-8") as f:
        json.dump({"cell": met, "events": em, "theta12": em12}, f, indent=2, default=str)
    with open(RES7 / "GATE_7.json", "w", encoding="utf-8") as f:
        json.dump({"gates": gates, "decision": decision, "verdict": verdict}, f, indent=2, default=str)
    pd.DataFrame({"date": pd.to_datetime(d["val_dates"]), "score": sc,
                  "label_y": d["y_val"], "future_return": d["y_future_val"],
                  "event": ev_mask}).to_parquet(RES7 / "oof7.parquet")
    manifest = {"H": H, "seed": SEED, "cost_C": COST_C, "n_boot": N_BOOT,
                "boot_K_events": BOOT_K, "cpu_hours": budget["cpu_hours"],
                "decision": decision, "verdict": verdict,
                "holdout": "UNTOUCHED (P5/B/C/A)"}
    with open(RES7 / "MANIFEST_7.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    write_report(out, manifest, d)
    print(f"\nKarar: {verdict}\nCPU: {budget['cpu_hours']:.3f} cpu-sa "
          f"duvar: {(time.time()-t_start)/60:.1f} dk", flush=True)


def _train_scores(d):
    sc, _ = fit_scores(d["X_train"], d["y_train"], d["X_train"])
    return sc


def write_report(out, manifest, d):
    m = out["cell"]
    e = out["events"]
    p = m["pss"]
    x = out["extra"]
    md = []
    md.append("# PHASE 7 — RUN REPORT (H48, DESIGN_700 locked)")
    md.append("")
    md.append(f"**Karar:** {out['verdict']} (exploratory-survival yorumu; confirmatory DEGIL, §0b)")
    md.append(f"**CPU:** {out['budget']['cpu_hours']:.3f} / 12 cpu-sa "
              f"({len(out['budget']['ledger'])} fit)")
    md.append("**Koruma:** P5/B/C/A DOKUNULMADI.")
    md.append("")
    md.append(f"1. θ48 = {e['theta']:+.4f}")
    md.append(f"2. CI95 = {e['ci95']} (event-block bootstrap K=500, 10k, s42)")
    md.append(f"3. PSS = {p['pss']:+.6f}")
    md.append(f"4. edge/cost = {p['edge_over_cost']:.3f}")
    md.append(f"5. AUC = {m['auc']:.4f}")
    md.append(f"6. rank-IC = {m['rank_ic']:.4f}")
    md.append(f"7. Kendall tau = {m['kendall_tau']:.4f}")
    md.append(f"8. MaxDD = {e['maxdd']}")
    md.append(f"9. WF consistency = {out['extra'].get('wf', {}).get('consistency', 'N/A (aday yolu kapali)')}")
    md.append(f"10. turnover = {x['turnover']}")
    md.append(f"11. gross return (event mean) = {e['gross']:+.6f}")
    md.append(f"12. cost impact = C={COST_C} (net = {e['mean_net']:+.6f})")
    md.append(f"13. event count = {e['n']} (rate VAL)")
    md.append(f"14. power = {p['power']:.2f}, d = {p['cohens_d']:+.3f}")
    md.append(f"15. gates = {out['gates']}")
    md.append(f"16. {out['verdict']}")
    md.append(f"theta12 comparator: {x['theta12']} (betimsel, ayni konstruksiyon; "
              f"Delta = {out['delta_theta_vs_H12']:+.4f}, karar URETMEZ)")
    with open(A7 / "PHASE_07_RUN_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    main()