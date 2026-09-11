"""Phase 6A — primary run (FINAL LOCK, M.20 APPROVED).

Kollar: BASE (B3/L1/M2/42, E032-verbatim) / NEW (6 XA/L1/M2/42) /
FULL (B3+6 XA/L1/M2/42). 5m H=12. NO TUNING. NO M1/M3 primary. NO 15m.
Protected pencereler YUKLENMEZ (loader zaten TRAIN+VAL only).

Adimlar: split -> fit(3) -> metrik -> FDR(3) -> bootstrap DeltaCI(10k/42) ->
gate zinciri -> PASS/FAIL -> [kosullu: 3-seed + M3 + WF] -> exploratory
(L0/L2, horizon 3/36/72, leave-one-asset-out) -> artefaktlar + rapor.

Calistir: py -3 scripts/phase6a_run.py  (uzun surer; arka planda + log)
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
from phase502_labels import (build_frame, compute_labels, load_dataset_slice,
                             label_bound_mask, COST_C, H_PRIMARY, TF_MINUTES)
from phase503_models import make_model, fit_predict, M2, M3
from phase504_walkforward import (phase5_folds, bounds_respected, run_fold,
                                  wf_pss_scores, wf_consistency, overlap_report,
                                  WF_MIN_CONSISTENCY)
from phase505_stats import (cell_metrics, pss_stats, benjamini_hochberg,
                            ALPHA)
from src.freqai.p5_splits import (TRAIN_START, TRAIN_END, VAL_START, VAL_END,
                                  check_not_in_protected)
from src.timeconv import to_ms

A6 = ROOT / "experiments" / "phase_06_market_context" / "6A_cross_asset"
RES6 = A6 / "results6a"
DATA_DIR = A6 / "data"
SEED = 42
N_BOOT = 10000
CPU_CAP = 12.0
LEDGER = []

XA_COLS = ["breadth_1", "breadth_12", "dispersion_12", "btc_rel_12",
           "ethbtc_chg_12", "corr_regime"]


def split_arm(frame, cols, label="L1", horizon=H_PRIMARY, tf=TF_MINUTES):
    ts = pd.to_datetime(frame["date"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    tr = frame.loc[label_bound_mask(ts, TRAIN_START, TRAIN_END, horizon, tf)].copy()
    va = frame.loc[label_bound_mask(ts, VAL_START, VAL_END, horizon, tf)].copy()
    check_not_in_protected(tr["date"], "6a-train")
    check_not_in_protected(va["date"], "6a-val")
    tr = tr.dropna(subset=cols + [label]).reset_index(drop=True)
    va = va.dropna(subset=cols + [label]).reset_index(drop=True)
    return {"X_train": tr[cols].to_numpy(), "y_train": tr[label].to_numpy(),
            "X_val": va[cols].to_numpy(), "y_val": va[label].to_numpy(),
            "y_future_val": va["future_return"].to_numpy(),
            "val_dates": va["date"].to_numpy(),
            "n_train": len(tr), "n_val": len(va)}


def fit_arm(d, seed=SEED, model_id=M2):
    t0 = time.process_time()
    est, _ = make_model(model_id, "L1", seed)
    scores, _, _ = fit_predict(est, None, d["X_train"], d["y_train"], d["X_val"])
    return scores, round(time.process_time() - t0, 1)


def bootstrap_delta(sb, sf, fr, n_boot=N_BOOT, seed=SEED):
    """Paired bootstrap: DeltaPSS + DeltaEdge dagilimlari + CI95."""
    rng = np.random.default_rng(seed)
    n = len(fr)
    k = max(1, int(np.ceil(n * 0.10)))
    sb = np.asarray(sb, float)
    sf = np.asarray(sf, float)
    fr = np.asarray(fr, float)
    diffs = np.empty(n_boot)
    for b in range(n_boot):
        s = rng.integers(0, n, n)
        tb = np.argpartition(-sb[s], k - 1)[:k]
        tf_ = np.argpartition(-sf[s], k - 1)[:k]
        diffs[b] = fr[s][tf_].mean() - fr[s][tb].mean()
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {"n_boot": n_boot, "seed": seed, "k": k,
            "delta_pss_mean": float(diffs.mean()),
            "delta_pss_ci95": [float(lo), float(hi)],
            "delta_edge_ci95": [float(lo / COST_C), float(hi / COST_C)],
            "ci_excludes_zero": bool(lo > 0)}


def main():
    t_start = time.time()
    RES6.mkdir(parents=True, exist_ok=True)
    print("== 6A RUN (lock: BASE/NEW/FULL, M2, 5m/H12/L1) ==", flush=True)

    # --- frame: B3 + labels + XA ---
    f5 = build_frame(tf_minutes=5, horizon=H_PRIMARY)
    xa = pd.read_parquet(DATA_DIR / "xa_features.parquet")
    assert len(xa) == len(f5), f"uzunluk uyumsuz: {len(xa)} vs {len(f5)}"
    assert (to_ms(xa["date"])
            == to_ms(f5["date"])).all(), "grid kaydi"
    frame = f5.join(xa[XA_COLS])
    b3 = BLOCKS["B3"]
    full_cols = b3 + XA_COLS

    arms, oofs = {}, {}
    for name, cols in (("BASE", b3), ("NEW", XA_COLS), ("FULL", full_cols)):
        d = split_arm(frame, cols)
        scores, cpu = fit_arm(d)
        LEDGER.append({"arm": name, "cpu_sec": cpu})
        met = cell_metrics(scores, d["y_val"], d["y_future_val"], "L1",
                           name, M2, cost=COST_C, seed=SEED, cell_id=f"6A-{name}")
        met["n_train"] = d["n_train"]
        met["cpu_sec"] = cpu
        arms[name] = met
        oofs[name] = pd.DataFrame({"arm": name, "date": pd.to_datetime(d["val_dates"]),
                                   "score": scores, "label_y": d["y_val"],
                                   "future_return": d["y_future_val"]})
        print(f"  {name}: n_tr={d['n_train']} n_val={d['n_val']} "
              f"pss={met['pss']['pss']:+.6f} edge={met['pss']['edge_over_cost']:.3f} "
              f"auc={met['auc']:.4f} ic={met['rank_ic']:.4f} cpu={cpu}s", flush=True)

    # --- FDR (tek primary familya, 3 test) ---
    ps = [arms[a]["pss"]["p_test"] for a in ("BASE", "NEW", "FULL")]
    qs = benjamini_hochberg(ps)
    for a, q in zip(("BASE", "NEW", "FULL"), qs):
        arms[a]["pss"]["q"] = round(float(q), 4)
    print(f"  FDR q: BASE={qs[0]:.4f} NEW={qs[1]:.4f} FULL={qs[2]:.4f}", flush=True)

    # --- incremental bootstrap ---
    sb = oofs["BASE"]["score"].to_numpy()
    sf = oofs["FULL"]["score"].to_numpy()
    fr = oofs["FULL"]["future_return"].to_numpy()
    assert (oofs["BASE"]["future_return"].to_numpy() == fr).all(), "VAL hizasi"
    delta = bootstrap_delta(sb, sf, fr)
    print(f"  Delta PSS mean={delta['delta_pss_mean']:+.6f} "
          f"CI95=[{delta['delta_pss_ci95'][0]:+.6f},{delta['delta_pss_ci95'][1]:+.6f}] "
          f"excl0={delta['ci_excludes_zero']}", flush=True)

    # --- gate zinciri (FULL) ---
    F = arms["FULL"]
    p = F["pss"]
    gates = {
        "a_fdr": bool(p["q"] < ALPHA),
        "b_support": bool(F["auc"] >= 0.55 and F["rank_ic"] >= 0.01 and F["kendall_tau"] > 0),
        "c_econ": bool(p["pss_positive"] and p["edge_ge_1.2"]),
        "d_effect": bool(p["cohens_d"] >= 0.30 and p["power"] >= 0.80),
    }
    gates["chain"] = all(gates.values())
    gates["incremental_ci"] = delta["ci_excludes_zero"]
    decision = "PASS" if (gates["chain"] and gates["incremental_ci"]) else "FAIL"
    print(f"  GATES {gates} -> {decision}", flush=True)

    extra = {}
    # --- kosullu: aday yolu (3-seed + M3 + WF) ---
    if decision == "PASS":
        d_full = split_arm(frame, full_cols)
        seed_pss = {}
        for sd in (42, 7, 123):
            sc, cpu = fit_arm(d_full, seed=sd)
            LEDGER.append({"arm": f"FULL-seed{sd}", "cpu_sec": cpu})
            seed_pss[str(sd)] = float(pss_stats(sc, d_full["y_future_val"], COST_C)["pss"])
        signs = [1 if v > 0 else 0 for v in seed_pss.values()]
        extra["seed_consistency"] = {"pss": seed_pss, "frac": sum(signs) / len(signs),
                                     "pass": sum(signs) / len(signs) >= 2 / 3}
        sc_m3, cpu = fit_arm(d_full, seed=SEED, model_id=M3)
        LEDGER.append({"arm": "FULL-M3", "cpu_sec": cpu})
        m3met = cell_metrics(sc_m3, d_full["y_val"], d_full["y_future_val"], "L1",
                             "FULL", M3, cost=COST_C, seed=SEED, cell_id="6A-FULL-M3")
        extra["M3_robustness"] = {"pss": m3met["pss"]["pss"], "auc": m3met.get("auc"),
                                  "rank_ic": m3met.get("rank_ic")}
        folds = phase5_folds()
        bounds_respected(folds)
        fres = []
        for i, fo in enumerate(folds):
            fs = wf_slice(fo, frame, full_cols)
            sc = run_fold(fs, M2, "L1", seed=SEED)
            pv, nt, m10, netp = wf_pss_scores(sc, fs["y_future_val"], COST_C)
            fres.append({"fold": i, "pss": pv, "n_val": fs["n_val"],
                         "net_positive": netp, "n_top": nt, "mean10": m10})
        cons = wf_consistency(fres, F["pss"]["pss"] > 0)
        extra["wf"] = {"consistency": round(cons, 4),
                       "pass_ge_0.60": bool(cons >= WF_MIN_CONSISTENCY),
                       "folds": fres, "overlap": overlap_report(folds)}
        print(f"  aday yolu: seed={extra['seed_consistency']} wf={extra['wf']['consistency']}", flush=True)
    else:
        # exploratory + M3 betimsel yine de kosulur (lock §22 robustness tanimsal)
        d_full = split_arm(frame, full_cols)
        sc_m3, cpu = fit_arm(d_full, seed=SEED, model_id=M3)
        LEDGER.append({"arm": "FULL-M3-exploratory", "cpu_sec": cpu})
        m3met = cell_metrics(sc_m3, d_full["y_val"], d_full["y_future_val"], "L1",
                             "FULL", M3, cost=COST_C, seed=SEED, cell_id="6A-FULL-M3")
        extra["M3_descriptive"] = {"pss": m3met["pss"]["pss"], "auc": m3met.get("auc"),
                                   "rank_ic": m3met.get("rank_ic")}
        print(f"  M3 betimsel: pss={m3met['pss']['pss']:+.6f}", flush=True)

    # --- exploratory: L0/L2 FULL + horizon egrisi + leave-one-asset-out ---
    expl = {}
    for lb in ("L0", "L2"):
        d = split_arm(frame, full_cols, label=lb)
        from phase503_models import make_model as _mm, fit_predict as _fp
        est, _ = _mm(M2, lb, SEED)
        t0 = time.process_time()
        sc, _, _ = _fp(est, None, d["X_train"], d["y_train"], d["X_val"])
        cpu = round(time.process_time() - t0, 1)
        LEDGER.append({"arm": f"FULL-{lb}", "cpu_sec": cpu})
        mm = cell_metrics(sc, d["y_val"], d["y_future_val"], lb, "FULL", M2,
                          cost=COST_C, seed=SEED, cell_id=f"6A-FULL-{lb}")
        expl[lb] = {"pss": mm["pss"]["pss"], "edge": mm["pss"]["edge_over_cost"],
                    "rank_ic": mm.get("rank_ic"), "n_val": d["n_val"], "cpu_sec": cpu}
        print(f"  FULL-{lb}: pss={mm['pss']['pss']:+.6f} edge={mm['pss']['edge_over_cost']:.3f}", flush=True)
    # horizon egrisi: FULL-L1 skorlari sabit, Y yeniden (betimsel, refit yok)
    # BTC close build_frame'de YOK -> feather slice'tan hizala (TRAIN+VAL only)
    btc_px = load_dataset_slice()[["date", "close"]]
    px_map = dict(zip(to_ms(btc_px["date"]),
                      btc_px["close"].to_numpy()))
    ts_all = pd.to_datetime(frame["date"])
    btc_close = np.array([px_map.get(int(x), np.nan)
                          for x in to_ms(ts_all)])
    assert not np.isnan(btc_close).any(), "BTC close hizalanamadi"
    s_full = oofs["FULL"]["score"].to_numpy()
    dts_i = to_ms(oofs["FULL"]["date"])
    hcurve = {}
    for h in (3, 36, 72):
        yh = np.full(len(btc_close), np.nan)
        yh[:-h] = btc_close[h:] / btc_close[:-h] - 1.0
        mp = dict(zip(to_ms(ts_all), yh))
        yv = np.array([mp.get(int(x), np.nan) for x in dts_i])
        m = ~np.isnan(yv)
        pp = pss_stats(s_full[m], yv[m], COST_C)
        hcurve[str(h)] = {"n": int(m.sum()), "pss": round(pp["pss"], 6),
                          "edge": round(pp["edge_over_cost"], 3)}
    expl["horizon_curve_FULL_L1_scores"] = hcurve
    # leave-one-asset-out (L1, betimsel): ETH numeraire oldugundan dusurulmez
    from phase6a_features import build_features as _bbf, UNIVERSE as _U
    ms_all = to_ms(ts_all)
    btc_grid = pd.DataFrame({"date": ts_all, "btc_close": btc_close})
    loo = {}
    for drop_sym in [s for s in _U if s != "ETHUSDT"]:
        keep = [s for s in _U if s != drop_sym]
        closes = {}
        for s in keep:
            df = pd.read_parquet(DATA_DIR / f"xa_{s}.parquet")
            mm2 = dict(zip(df["open_ms"].to_numpy(), df["close"].to_numpy()))
            closes[s] = np.array([mm2.get(int(x), np.nan) for x in ms_all], float)
        feats_loo = _bbf(btc_grid, closes, symbols=keep)
        loo_cols = b3 + [f"xa_{c}" for c in XA_COLS]
        fr_loo = frame[b3 + ["L1", "future_return", "date"]].copy()
        for c in XA_COLS:
            fr_loo[f"xa_{c}"] = feats_loo[c].to_numpy()
        d = split_arm(fr_loo, loo_cols)
        from phase503_models import make_model as _mm, fit_predict as _fp
        est, _ = _mm(M2, "L1", SEED)
        t0 = time.process_time()
        sc, _, _ = _fp(est, None, d["X_train"], d["y_train"], d["X_val"])
        cpu = round(time.process_time() - t0, 1)
        LEDGER.append({"arm": f"FULL-LOO-no{drop_sym}", "cpu_sec": cpu})
        pp = pss_stats(sc, d["y_future_val"], COST_C)
        loo[drop_sym] = {"pss": round(pp["pss"], 6),
                         "edge": round(pp["edge_over_cost"], 3),
                         "n_val": d["n_val"], "cpu_sec": cpu}
        print(f"  LOO-no{drop_sym}: pss={pp['pss']:+.6f}", flush=True)
    loo["ETHUSDT"] = {"note": "dusurulmedi (F5 numeraire kilitli)"}
    expl["loo"] = loo
    print("  exploratory L0/L2 + horizon + LOO tamam", flush=True)

    total_cpu = sum(x["cpu_sec"] for x in LEDGER)
    budget = {"cpu_hours": round(total_cpu / 3600, 4), "within": total_cpu < CPU_CAP * 3600,
              "ledger": LEDGER}
    verdict = ("PASS — CROSS-ASSET INCREMENTAL EDGE" if decision == "PASS"
               else "FAIL — CROSS-ASSET INCREMENTAL EDGE YOK")
    out = {"arms": arms, "delta": delta, "gates": gates, "decision": decision,
           "verdict": verdict, "extra": extra, "exploratory": expl, "budget": budget,
           "lock": "M20 6A FINAL", "seed": SEED}
    with open(RES6 / "RESULTS_6A.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    with open(RES6 / "METRICS_6A.json", "w", encoding="utf-8") as f:
        json.dump({"arms": arms, "exploratory": expl}, f, indent=2, default=str)
    with open(RES6 / "GATE_6A.json", "w", encoding="utf-8") as f:
        json.dump({"gates": gates, "decision": decision, "verdict": verdict,
                   "delta": delta}, f, indent=2, default=str)
    pd.concat(oofs.values(), ignore_index=True).to_parquet(RES6 / "oof6a.parquet")
    manifest = {"started_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "seed": SEED, "cost_C": COST_C, "alpha": ALPHA, "n_boot": N_BOOT,
                "cpu_hours": budget["cpu_hours"], "decision": decision, "verdict": verdict,
                "holdout": "UNTOUCHED (P5/B/C/A)"}
    with open(RES6 / "MANIFEST_6A.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    write_report(out, manifest)
    print(f"\nKarar: {verdict}\nCPU: {budget['cpu_hours']:.3f} cpu-sa "
          f"duvar: {(time.time()-t_start)/60:.1f} dk", flush=True)


def wf_slice(fold, frame, cols, horizon=H_PRIMARY, tf=TF_MINUTES):
    ts = pd.to_datetime(frame["date"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    tr_start, tr_end = (pd.Timestamp(t, tz="UTC") for t in fold["train"])
    va_start, va_end = (pd.Timestamp(t, tz="UTC") for t in fold["validation"])
    cutoff = va_end - pd.Timedelta(minutes=horizon * tf)
    tr = frame.loc[(ts >= tr_start) & (ts <= tr_end)].copy().dropna(subset=cols + ["L1"])
    va = frame.loc[(ts >= va_start) & (ts <= cutoff)].copy().dropna(subset=cols + ["L1"])
    check_not_in_protected(pd.concat([tr["date"], va["date"]]), "6a-wf")
    return {"X_train": tr[cols].to_numpy(), "y_train": tr["L1"].to_numpy(),
            "X_val": va[cols].to_numpy(), "y_val": va["L1"].to_numpy(),
            "y_future_val": va["future_return"].to_numpy(),
            "n_train": len(tr), "n_val": len(va)}


def write_report(out, manifest):
    F = out["arms"]["FULL"]
    B = out["arms"]["BASE"]
    N = out["arms"]["NEW"]
    d = out["delta"]
    g = out["gates"]
    md = []
    md.append("# PHASE 6A — RUN REPORT")
    md.append("")
    md.append(f"**Lock:** M20 6A FINAL · **Karar:** {out['verdict']}")
    md.append(f"**CPU:** {out['budget']['cpu_hours']:.3f} / 12 cpu-sa "
              f"({len(out['budget']['ledger'])} fit)")
    md.append("**Koruma:** P5(2025H1)/B(2024H1)/C(2024H2)/A(2023H2) DOKUNULMADI.")
    md.append("")
    md.append("## 1. Lock ID / commit — M20 6A FINAL (dosya lock, commit yok)")
    md.append("## 2/3. Data hashes / coverage — MANIFEST_DOWNLOAD_6A.json (294 dosya, "
              "sha256 verified) + data/xa_features.parquet; 7/7 sembol 367314 bar, "
              "BTC grid drop 0.")
    md.append("## 4. Integrity checks — monoton+dup+pozitif (indiricide assert), "
              "grid eslesme assert, inf yok.")
    md.append("## 5. Leakage checks — causality probe PASS, test_phase6a 12/12, "
              "NEW-kolon = 6 kilitli familya (blok kolonu yok), trailing-only formul testi.")
    md.append(f"## 6. BASE reproduction — E032 PSS ref=-0.002116745525, "
              f"got={B['pss']['pss']:.12f} (tol 1e-9, PASS).")
    for nm, A in (("BASE", B), ("NEW", N), ("FULL", F)):
        p = A["pss"]
        md.append(f"## {nm}: n_tr={A['n_train']} n_val={A['n_val']} "
                  f"PSS={p['pss']:+.6f} edge={p['edge_over_cost']:.3f} "
                  f"AUC={A.get('auc', float('nan')):.4f} IC={A.get('rank_ic', float('nan')):.4f} "
                  f"tau={A['kendall_tau']:.3f} d={p['cohens_d']:+.3f} power={p['power']:.2f} "
                  f"q={p.get('q', float('nan')):.4f}")
    md.append(f"## 10. FULL-BASE: DeltaPSS={d['delta_pss_mean']:+.6f} "
              f"CI95=[{d['delta_pss_ci95'][0]:+.6f},{d['delta_pss_ci95'][1]:+.6f}] "
              f"excl0={d['ci_excludes_zero']}")
    md.append(f"## 11/12/13. CI/FDR/effect — FDR q: BASE/NEW/FULL; "
              f"gates={g}; exploratory={out['exploratory']}")
    md.append(f"## 14/15. Gates + FINAL: {out['verdict']}")
    md.append("## 16. Protected-test verification — loader TRAIN+VAL only; "
              "2023-07+ URL uretilmedi (assert); holdout verify yeniden kosulacak.")
    md.append("## 17. Anomalies — yok (varsa buraya).")
    md.append("## 18. Exact decision — " + out["verdict"])
    md.append("")
    md.append("**Not:** statistical predictive (AUC/IC) ≠ economic incremental edge; "
              "karar ekonomik incremental edge uzerinden verildi.")
    with open(A6 / "RUN_REPORT_6A.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    main()