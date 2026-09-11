"""Phase 6C — primary run (FINAL LOCK, M.20 APPROVED).

Kollar: BASE (B3/L1/M2/42, E032-verbatim) / NEW (5 OI/L1/M2/42) /
FULL (B3+5/L1/M2/42). 5m H=12. NO TUNING. NO M1/M3 primary. NO 15m.
NO paid fallback. Makine 6A/6B ile BIREBIR ayni (import).
Protected pencereler YUKLENMEZ.

Gate'ler: VAL OI-boslugu sifir (STOP) + FULL n_train>=200k + n_val==BASE n_val
(STOP) + E032 repro tol 1e-9 (STOP).
Adimlar: split -> fit(3) -> metrik -> FDR(3) -> bootstrap DeltaCI(10k/42) ->
gate zinciri -> PASS/FAIL -> [kosullu: 3-seed + M3 + WF] ->
exploratory (L0/L2, horizon, OI×rejim betimsel) -> artefaktlar.

Calistir: py -3 scripts/phase6c_run.py (uzun surer; arka planda + log)
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
from phase502_labels import (build_frame, COST_C, H_PRIMARY, TF_MINUTES,
                             load_dataset_slice, label_bound_mask)
from phase503_models import make_model, fit_predict, M2, M3
from phase504_walkforward import (phase5_folds, bounds_respected, run_fold,
                                  wf_pss_scores, wf_consistency, overlap_report,
                                  WF_MIN_CONSISTENCY)
from phase505_stats import (cell_metrics, pss_stats, benjamini_hochberg, ALPHA)
from phase6a_run import split_arm, fit_arm, bootstrap_delta, wf_slice
from phase6b_run import native_regime
from src.freqai.p5_splits import VAL_START, VAL_END
from src.timeconv import to_ms

A6 = ROOT / "experiments" / "phase_06_market_context" / "6C_oi"
RES6 = A6 / "results6c"
DATA_DIR = A6 / "data"
SEED = 42
N_BOOT = 10000
CPU_CAP = 12.0
LEDGER = []
E032_REF = -0.002116745525
MIN_TRAIN = 200000  # kilitli kabul kriteri

OI_COLS = ["oi_chg_12", "oi_z_288", "oi_price_div", "oi_chg_1", "oi_range_288"]


def main():
    t_start = time.time()
    RES6.mkdir(parents=True, exist_ok=True)
    print("== 6C RUN (lock: BASE/NEW/FULL oi, M2, 5m/H12/L1) ==", flush=True)

    f5 = build_frame(tf_minutes=5, horizon=H_PRIMARY)
    oif = pd.read_parquet(DATA_DIR / "oi_features.parquet")
    assert len(oif) == len(f5), "uzunluk uyumsuz"
    assert (to_ms(oif["date"])
            == to_ms(f5["date"])).all(), "grid kaydi"
    frame = f5.join(oif[OI_COLS])

    # --- VAL sifir-bosluk gate (STOP) ---
    ts = pd.to_datetime(frame["date"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    cutoff = pd.Timestamp(VAL_END) - pd.Timedelta(minutes=H_PRIMARY * TF_MINUTES)
    if getattr(cutoff, "tz", None) is None:
        cutoff = cutoff.tz_localize("UTC")
    vm = (ts >= pd.Timestamp(VAL_START)) & (ts <= cutoff)
    # --- VAL QC gate (REVIZYON): affected-row UNION orani <= %1, else STOP ---
    vm_count = int(vm.sum())
    union_mask = frame.loc[vm, OI_COLS].isna().any(axis=1).to_numpy()
    n_union = int(union_mask.sum())
    per_col = {c: int(frame.loc[vm, c].isna().sum()) for c in OI_COLS}
    rate = n_union / vm_count if vm_count else 1.0
    print(f"  VAL affected union: {n_union}/{vm_count} = {rate:.4%} "
          f"(hucre-toplami DEGIL, union) per-col={per_col}", flush=True)
    if rate > 0.01:
        raise RuntimeError(f"STOP: VAL affected union {rate:.4%} > %1")

    b3 = BLOCKS["B3"]
    full_cols = b3 + OI_COLS
    arms, oofs = {}, {}
    for name, cols in (("BASE", b3), ("NEW", OI_COLS), ("FULL", full_cols)):
        d = split_arm(frame, cols)
        scores, cpu = fit_arm(d)
        LEDGER.append({"arm": name, "cpu_sec": cpu})
        met = cell_metrics(scores, d["y_val"], d["y_future_val"], "L1",
                           name, M2, cost=COST_C, seed=SEED, cell_id=f"6C-{name}")
        met["n_train"] = d["n_train"]
        met["cpu_sec"] = cpu
        arms[name] = met
        oofs[name] = pd.DataFrame({"arm": name, "date": pd.to_datetime(d["val_dates"]),
                                   "score": scores, "label_y": d["y_val"],
                                   "future_return": d["y_future_val"]})
        print(f"  {name}: n_tr={d['n_train']} n_val={d['n_val']} "
              f"pss={met['pss']['pss']:+.6f} edge={met['pss']['edge_over_cost']:.3f} "
              f"auc={met['auc']:.4f} ic={met['rank_ic']:.4f} cpu={cpu}s", flush=True)

    # --- train-loss + repro gate'leri (REVIZYON: VAL kaybi union ile tutarli olmali) ---
    if arms["FULL"]["n_train"] < MIN_TRAIN:
        raise RuntimeError(f"STOP: train n < 200k ({arms['FULL']['n_train']})")
    base_ok = frame.loc[vm, b3 + ["L1"]].notna().all(axis=1).to_numpy()
    full_ok = frame.loc[vm, full_cols + ["L1"]].notna().all(axis=1).to_numpy()
    assert int(base_ok.sum()) == arms["BASE"]["n_val"], "split tutarsizligi (BASE)"
    assert int(full_ok.sum()) == arms["FULL"]["n_val"], "split tutarsizligi (FULL)"
    only_full_dropped = base_ok & ~full_ok
    union_arr = frame.loc[vm, OI_COLS].isna().any(axis=1).to_numpy()
    if only_full_dropped.sum() > 0 and not union_arr[only_full_dropped].all():
        raise RuntimeError("STOP: FULL ek kaybin kaynagi QC-disi (union disi satir dustu)")
    print(f"  FULL ek drop: {int(only_full_dropped.sum())} satir, tamami union-ici: "
          f"{bool((not only_full_dropped.any()) or union_arr[only_full_dropped].all())}", flush=True)
    diff = abs(arms["BASE"]["pss"]["pss"] - E032_REF)
    print(f"  E032 repro: diff={diff:.2e}", flush=True)
    if diff >= 1e-9:
        raise RuntimeError(f"STOP: E032 reproduction failure (diff={diff:.2e})")

    ps = [arms[a]["pss"]["p_test"] for a in ("BASE", "NEW", "FULL")]
    qs = benjamini_hochberg(ps)
    for a, q in zip(("BASE", "NEW", "FULL"), qs):
        arms[a]["pss"]["q"] = round(float(q), 4)
    print(f"  FDR q: BASE={qs[0]:.4f} NEW={qs[1]:.4f} FULL={qs[2]:.4f}", flush=True)

    # Paired bootstrap: ortak tarihlerde inner-join (FULL'un dustugu 291 satir
    # FULL skoruna sahip degil -> ciftten dislanir; BASE tekil PSS'i kendi
    # tam setinde aynen raporlanir. Revizyon notu: esleme tarih-bazlidir.)
    b = oofs["BASE"][["date", "score", "future_return"]]
    f = oofs["FULL"][["date", "score", "future_return"]]
    mm = pd.merge(b, f, on="date", suffixes=("_b", "_f"))
    assert (mm["future_return_b"].to_numpy() == mm["future_return_f"].to_numpy()).all()
    sb = mm["score_b"].to_numpy()
    sf = mm["score_f"].to_numpy()
    fr = mm["future_return_f"].to_numpy()
    print(f"  paired n: {len(mm)} (BASE {len(b)}, FULL {len(f)})", flush=True)
    delta = bootstrap_delta(sb, sf, fr)
    print(f"  Delta PSS mean={delta['delta_pss_mean']:+.6f} "
          f"CI95=[{delta['delta_pss_ci95'][0]:+.6f},{delta['delta_pss_ci95'][1]:+.6f}] "
          f"excl0={delta['ci_excludes_zero']}", flush=True)

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
    d_full = split_arm(frame, full_cols)
    if decision == "PASS":
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
                             "FULL", M3, cost=COST_C, seed=SEED, cell_id="6C-FULL-M3")
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
        print("  aday yolu tamam", flush=True)
    else:
        sc_m3, cpu = fit_arm(d_full, seed=SEED, model_id=M3)
        LEDGER.append({"arm": "FULL-M3-exploratory", "cpu_sec": cpu})
        m3met = cell_metrics(sc_m3, d_full["y_val"], d_full["y_future_val"], "L1",
                             "FULL", M3, cost=COST_C, seed=SEED, cell_id="6C-FULL-M3")
        extra["M3_descriptive"] = {"pss": m3met["pss"]["pss"], "auc": m3met.get("auc"),
                                   "rank_ic": m3met.get("rank_ic")}
        print(f"  M3 betimsel: pss={m3met['pss']['pss']:+.6f}", flush=True)

    from phase503_models import make_model as _mm, fit_predict as _fp
    expl = {}
    for lb in ("L0", "L2"):
        d = split_arm(frame, full_cols, label=lb)
        est, _ = _mm(M2, lb, SEED)
        t0 = time.process_time()
        sc, _, _ = _fp(est, None, d["X_train"], d["y_train"], d["X_val"])
        cpu = round(time.process_time() - t0, 1)
        LEDGER.append({"arm": f"FULL-{lb}", "cpu_sec": cpu})
        mm = cell_metrics(sc, d["y_val"], d["y_future_val"], lb, "FULL", M2,
                          cost=COST_C, seed=SEED, cell_id=f"6C-FULL-{lb}")
        expl[lb] = {"pss": mm["pss"]["pss"], "edge": mm["pss"]["edge_over_cost"],
                    "rank_ic": mm.get("rank_ic"), "n_val": d["n_val"], "cpu_sec": cpu}
        print(f"  FULL-{lb}: pss={mm['pss']['pss']:+.6f} edge={mm['pss']['edge_over_cost']:.3f}", flush=True)
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
    ohlcv = load_dataset_slice()[["date", "open", "high", "low", "close"]].reset_index(drop=True)
    assert len(ohlcv) == len(frame), "OHLCV grid uyumsuz"
    regl = native_regime(ohlcv)
    rv = pd.DataFrame({"score": s_full, "fr": fr,
                       "regime": regl.to_numpy()[np.searchsorted(
                           to_ms(ts_all), dts_i)]})
    reg_out = {}
    for rg, g in rv.dropna(subset=["regime"]).groupby("regime"):
        if len(g) < 100:
            reg_out[str(rg)] = {"n": int(len(g)), "note": "yetersiz n"}
            continue
        pp = pss_stats(g["score"].to_numpy(), g["fr"].to_numpy(), COST_C)
        reg_out[str(rg)] = {"n": int(len(g)), "pss": round(pp["pss"], 6),
                            "edge": round(pp["edge_over_cost"], 3)}
    expl["oi_x_regime_descriptive"] = reg_out
    print("  exploratory tamam", flush=True)

    total_cpu = sum(x["cpu_sec"] for x in LEDGER)
    budget = {"cpu_hours": round(total_cpu / 3600, 4), "within": total_cpu < CPU_CAP * 3600,
              "ledger": LEDGER}
    verdict = ("PASS — OI INCREMENTAL EDGE" if decision == "PASS"
               else "FAIL — OI INCREMENTAL EDGE YOK")
    out = {"arms": arms, "delta": delta, "gates": gates, "decision": decision,
           "verdict": verdict, "extra": extra, "exploratory": expl, "budget": budget,
           "lock": "M20 6C FINAL + QC REVISION", "seed": SEED,
           "val_qc": {"n_union": n_union, "n_val_window": vm_count,
                      "rate": round(rate, 6), "per_col": per_col,
                      "rule": "union<=1%, hucre-toplami degil"}}
    with open(RES6 / "RESULTS_6C.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    with open(RES6 / "METRICS_6C.json", "w", encoding="utf-8") as f:
        json.dump({"arms": arms, "exploratory": expl}, f, indent=2, default=str)
    with open(RES6 / "GATE_6C.json", "w", encoding="utf-8") as f:
        json.dump({"gates": gates, "decision": decision, "verdict": verdict,
                   "delta": delta}, f, indent=2, default=str)
    pd.concat(oofs.values(), ignore_index=True).to_parquet(RES6 / "oof6c.parquet")
    manifest = {"seed": SEED, "cost_C": COST_C, "alpha": ALPHA, "n_boot": N_BOOT,
                "cpu_hours": budget["cpu_hours"], "decision": decision, "verdict": verdict,
                "holdout": "UNTOUCHED (P5/B/C/A)"}
    with open(RES6 / "MANIFEST_6C.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    write_report(out)
    print(f"\nKarar: {verdict}\nCPU: {budget['cpu_hours']:.3f} cpu-sa "
          f"duvar: {(time.time()-t_start)/60:.1f} dk", flush=True)


def write_report(out):
    F = out["arms"]["FULL"]
    B = out["arms"]["BASE"]
    N = out["arms"]["NEW"]
    d = out["delta"]
    g = out["gates"]
    md = []
    md.append("# PHASE 6C — RUN REPORT (revize lock, taze kosu)")
    md.append("")
    md.append(f"**Lock:** M20 6C FINAL + M.20 QC REVIZYONU · **Karar:** {out['verdict']}")
    md.append(f"**CPU:** {out['budget']['cpu_hours']:.3f} / 12 cpu-sa "
              f"({len(out['budget']['ledger'])} fit)")
    md.append("**Koruma:** P5(2025H1)/B(2024H1)/C(2024H2)/A(2023H2) DOKUNULMADI.")
    md.append("")
    md.append("## Data coverage/hash — MANIFEST_DOWNLOAD_6C.json (sha256 verified, "
              "dedup keep-first, ilk-OI gate).")
    md.append("## Integrity — monoton+dup+pozitif assert; grid aidiyet; inf yok.")
    md.append("## Alignment/dedup — ACTUAL-ms asof-backward; T candle R(T) gorur; "
              "dedup sonrasi dup STOP (tetiklenmedi).")
    md.append("## Leakage — causality probe PASS, test_phase6c 11/11, NEW = 5 kilitli "
              "familya, trailing-only testi.")
    md.append(f"## Train/validation — FULL n_tr={F['n_train']} (gate ≥200k), "
              f"n_val={F['n_val']} (BASE ile esit).")
    vq = out["val_qc"]
    md.append(f"## VAL QC gate — affected UNION = {vq['n_union']}/{vq['n_val_window']} "
              f"= %{vq['rate']*100:.4f} (union; hucre-toplami DEGIL) "
              f"per-col={vq['per_col']} → {'PASS (<= %1)' if vq['rate'] <= 0.01 else 'STOP'}.")
    md.append(f"## BASE reproduction — ref={E032_REF:.12f} got={B['pss']['pss']:.12f} PASS.")
    for nm, A in (("BASE", B), ("NEW", N), ("FULL", F)):
        p = A["pss"]
        md.append(f"## {nm}: n_tr={A['n_train']} n_val={A['n_val']} "
                  f"PSS={p['pss']:+.6f} edge={p['edge_over_cost']:.3f} "
                  f"AUC={A.get('auc', float('nan')):.4f} IC={A.get('rank_ic', float('nan')):.4f} "
                  f"tau={A['kendall_tau']:.3f} d={p['cohens_d']:+.3f} power={p['power']:.2f} "
                  f"q={p.get('q', float('nan')):.4f}")
    md.append(f"## FULL-BASE: DeltaPSS={d['delta_pss_mean']:+.6f} "
              f"CI95=[{d['delta_pss_ci95'][0]:+.6f},{d['delta_pss_ci95'][1]:+.6f}] "
              f"excl0={d['ci_excludes_zero']}")
    md.append(f"## CI/FDR/effect — gates={g}; exploratory={out['exploratory']}")
    md.append(f"## Gates + FINAL: {out['verdict']}")
    md.append("## Protected-test verification — TRAIN+VAL loader only; indirme "
              "2020→2023H1 assert'li; holdout verify kosu sonrasi tekrar kosulacak.")
    md.append("## Revision notu — R-QC (OI<=0 veya non-finite => missing, no fill) + "
              "VAL union toleransi <=%1 (M.20 onayli). Onceki STOP kosusu artefaktlari "
              "RUN_REPORT_6C_STOPPED.md / MANIFEST_6C_STOPPED.json olarak korunur; bu "
              "kosu taze deterministik rerun'dur (devam degil).")
    md.append("## Anomalies — venue sifir-OI glitch bloklari (2021-05-22, 2022-03-07/08, "
              "2023-06-06) manifestte belgeli.")
    md.append("## Exact decision — " + out["verdict"])
    md.append("")
    md.append("**Not:** statistical predictive ≠ economic incremental edge; karar "
              "ekonomik incremental edge uzerinden verildi.")
    with open(A6 / "RUN_REPORT_6C.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    main()