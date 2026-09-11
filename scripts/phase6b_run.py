"""Phase 6B — primary run (FINAL LOCK, M.20 APPROVED).

Kollar: BASE (B3/L1/M2/42, E032-verbatim) / NEW (5 fund/L1/M2/42) /
FULL (B3+5/L1/M2/42). 5m H=12. NO TUNING. NO M1/M3 primary. NO 15m.
Makine 6A ile BIREBIR ayni (split_arm/fit_arm/bootstrap_delta import).
Protected pencereler YUKLENMEZ.

Adimlar: split -> fit(3) + E032 repro-check -> metrik -> FDR(3) ->
bootstrap DeltaCI(10k/42) -> gate zinciri -> PASS/FAIL ->
[kosullu: 3-seed + M3 + WF] -> exploratory (L0/L2, horizon,
funding×rejim betimsel, settlement-penceresi duyarlilik) -> artefaktlar.

Calistir: py -3 scripts/phase6b_run.py (uzun surer; arka planda + log)
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

from phase501_features import BLOCKS, _wilder_adx, _wilder_atr
from phase502_labels import (build_frame, COST_C, H_PRIMARY, TF_MINUTES,
                             load_dataset_slice)
from phase503_models import make_model, fit_predict, M2, M3
from phase504_walkforward import (phase5_folds, bounds_respected, run_fold,
                                  wf_pss_scores, wf_consistency, overlap_report,
                                  WF_MIN_CONSISTENCY)
from phase505_stats import (cell_metrics, pss_stats, benjamini_hochberg, ALPHA)
from phase6a_run import split_arm, fit_arm, bootstrap_delta, wf_slice
from src.timeconv import to_ms

A6 = ROOT / "experiments" / "phase_06_market_context" / "6B_funding"
RES6 = A6 / "results6b"
DATA_DIR = A6 / "data"
SEED = 42
N_BOOT = 10000
CPU_CAP = 12.0
LEDGER = []
E032_REF = -0.002116745525  # TRAIN_VALIDATION_RESULTS.md + 6A bit-exact teyitli

FUND_COLS = ["fund_rate", "fund_z_30", "fund_sign", "fund_abs_chg", "fund_persist"]


def native_regime(ohlcv):
    """Locked classifier kurali, native Wilder (talib yok; betimsel kullanim).

    trend: SMA50 vs SMA200 + ADX14>20; vol: ATR14 30-bar rank>0.70.
    Donus: 'bull_high_vol' bicimi etiketler (NaN warmup'ta).
    """
    close = ohlcv["close"].astype(float)
    sma_f = close.rolling(50, min_periods=50).mean()
    sma_s = close.rolling(200, min_periods=200).mean()
    adx = _wilder_adx(ohlcv["high"].astype(float), ohlcv["low"].astype(float),
                      close, 14) * 100.0
    atr = _wilder_atr(ohlcv["high"].astype(float), ohlcv["low"].astype(float),
                      close, 14)
    vol_rank = atr.rolling(30, min_periods=30).rank(pct=True)
    trend = pd.Series("sideways", index=ohlcv.index)
    trend[(sma_f > sma_s) & (adx > 20.0)] = "bull"
    trend[(sma_f < sma_s) & (adx > 20.0)] = "bear"
    vol = pd.Series("low_vol", index=ohlcv.index)
    vol[vol_rank > 0.70] = "high_vol"
    lab = trend + "_" + vol
    lab[sma_s.isna() | adx.isna() | vol_rank.isna()] = np.nan
    return lab


def main():
    t_start = time.time()
    RES6.mkdir(parents=True, exist_ok=True)
    print("== 6B RUN (lock: BASE/NEW/FULL fund, M2, 5m/H12/L1) ==", flush=True)

    f5 = build_frame(tf_minutes=5, horizon=H_PRIMARY)
    fu = pd.read_parquet(DATA_DIR / "fund_features.parquet")
    assert len(fu) == len(f5), "uzunluk uyumsuz"
    assert (to_ms(fu["date"])
            == to_ms(f5["date"])).all(), "grid kaydi"
    frame = f5.join(fu[FUND_COLS])
    b3 = BLOCKS["B3"]
    full_cols = b3 + FUND_COLS

    arms, oofs = {}, {}
    for name, cols in (("BASE", b3), ("NEW", FUND_COLS), ("FULL", full_cols)):
        d = split_arm(frame, cols)
        scores, cpu = fit_arm(d)
        LEDGER.append({"arm": name, "cpu_sec": cpu})
        met = cell_metrics(scores, d["y_val"], d["y_future_val"], "L1",
                           name, M2, cost=COST_C, seed=SEED, cell_id=f"6B-{name}")
        met["n_train"] = d["n_train"]
        met["cpu_sec"] = cpu
        arms[name] = met
        oofs[name] = pd.DataFrame({"arm": name, "date": pd.to_datetime(d["val_dates"]),
                                   "score": scores, "label_y": d["y_val"],
                                   "future_return": d["y_future_val"]})
        print(f"  {name}: n_tr={d['n_train']} n_val={d['n_val']} "
              f"pss={met['pss']['pss']:+.6f} edge={met['pss']['edge_over_cost']:.3f} "
              f"auc={met['auc']:.4f} ic={met['rank_ic']:.4f} cpu={cpu}s", flush=True)

    # --- E032 reproduction gate (tol 1e-9; tutmazsa STOP) ---
    diff = abs(arms["BASE"]["pss"]["pss"] - E032_REF)
    print(f"  E032 repro: ref={E032_REF:.12f} got={arms['BASE']['pss']['pss']:.12f} "
          f"diff={diff:.2e}", flush=True)
    if diff >= 1e-9:
        raise RuntimeError(f"STOP: E032 reproduction failure (diff={diff:.2e})")

    ps = [arms[a]["pss"]["p_test"] for a in ("BASE", "NEW", "FULL")]
    qs = benjamini_hochberg(ps)
    for a, q in zip(("BASE", "NEW", "FULL"), qs):
        arms[a]["pss"]["q"] = round(float(q), 4)
    print(f"  FDR q: BASE={qs[0]:.4f} NEW={qs[1]:.4f} FULL={qs[2]:.4f}", flush=True)

    sb = oofs["BASE"]["score"].to_numpy()
    sf = oofs["FULL"]["score"].to_numpy()
    fr = oofs["FULL"]["future_return"].to_numpy()
    assert (oofs["BASE"]["future_return"].to_numpy() == fr).all(), "VAL hizasi"
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
                             "FULL", M3, cost=COST_C, seed=SEED, cell_id="6B-FULL-M3")
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
        print(f"  aday yolu tamam", flush=True)
    else:
        sc_m3, cpu = fit_arm(d_full, seed=SEED, model_id=M3)
        LEDGER.append({"arm": "FULL-M3-exploratory", "cpu_sec": cpu})
        m3met = cell_metrics(sc_m3, d_full["y_val"], d_full["y_future_val"], "L1",
                             "FULL", M3, cost=COST_C, seed=SEED, cell_id="6B-FULL-M3")
        extra["M3_descriptive"] = {"pss": m3met["pss"]["pss"], "auc": m3met.get("auc"),
                                   "rank_ic": m3met.get("rank_ic")}
        print(f"  M3 betimsel: pss={m3met['pss']['pss']:+.6f}", flush=True)

    # --- exploratory (gatesiz): L0/L2, horizon, funding×rejim, settlement penceresi ---
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
                          cost=COST_C, seed=SEED, cell_id=f"6B-FULL-{lb}")
        expl[lb] = {"pss": mm["pss"]["pss"], "edge": mm["pss"]["edge_over_cost"],
                    "rank_ic": mm.get("rank_ic"), "n_val": d["n_val"], "cpu_sec": cpu}
        print(f"  FULL-{lb}: pss={mm['pss']['pss']:+.6f} edge={mm['pss']['edge_over_cost']:.3f}", flush=True)
    # horizon egrisi (FULL-L1 skorlari sabit)
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
    # funding × rejim (betimsel; native kural, talib yok)
    ohlcv = load_dataset_slice()[["date", "open", "high", "low", "close"]].reset_index(drop=True)
    assert len(ohlcv) == len(frame), "OHLCV grid uyumsuz"
    regl = native_regime(ohlcv)
    rv = pd.DataFrame({"date": pd.to_datetime(oofs["FULL"]["date"]),
                       "score": s_full, "fr": fr, "regime": regl.loc[
                           regl.index.isin(pd.RangeIndex(len(frame)))].to_numpy()[
                           np.searchsorted(to_ms(ts_all), dts_i)]})
    reg_out = {}
    for rg, g in rv.dropna(subset=["regime"]).groupby("regime"):
        if len(g) < 100:
            reg_out[str(rg)] = {"n": int(len(g)), "note": "yetersiz n"}
            continue
        pp = pss_stats(g["score"].to_numpy(), g["fr"].to_numpy(), COST_C)
        reg_out[str(rg)] = {"n": int(len(g)), "pss": round(pp["pss"], 6),
                            "edge": round(pp["edge_over_cost"], 3)}
    expl["funding_x_regime_descriptive"] = reg_out
    # settlement penceresi duyarliligi: settlement ±1h maskesi (skor sabit)
    fund = pd.read_parquet(DATA_DIR / "funding_btcusdt.parquet")
    fms = fund["funding_ms"].to_numpy(dtype="int64")
    dms = dts_i // 10**6 if dts_i.max() > 10**15 else dts_i
    fms_ms = fms // 10**6 if fms.max() > 10**15 else fms
    nearest = np.abs(dms[:, None] - fms_ms[None, :]).min(axis=1)
    near = nearest <= 3600 * 1000  # ms cinsinden ±1h
    sens = {}
    for tag, m in (("within_1h", near), ("outside_1h", ~near)):
        if m.sum() < 100:
            sens[tag] = {"n": int(m.sum()), "note": "yetersiz n"}
            continue
        pp = pss_stats(s_full[m], fr[m], COST_C)
        sens[tag] = {"n": int(m.sum()), "pss": round(pp["pss"], 6),
                     "edge": round(pp["edge_over_cost"], 3)}
    expl["settlement_window_sensitivity"] = sens
    print("  exploratory tamam", flush=True)

    total_cpu = sum(x["cpu_sec"] for x in LEDGER)
    budget = {"cpu_hours": round(total_cpu / 3600, 4), "within": total_cpu < CPU_CAP * 3600,
              "ledger": LEDGER}
    verdict = ("PASS — FUNDING INCREMENTAL EDGE" if decision == "PASS"
               else "FAIL — FUNDING INCREMENTAL EDGE YOK")
    out = {"arms": arms, "delta": delta, "gates": gates, "decision": decision,
           "verdict": verdict, "extra": extra, "exploratory": expl, "budget": budget,
           "lock": "M20 6B FINAL", "seed": SEED}
    with open(RES6 / "RESULTS_6B.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    with open(RES6 / "METRICS_6B.json", "w", encoding="utf-8") as f:
        json.dump({"arms": arms, "exploratory": expl}, f, indent=2, default=str)
    with open(RES6 / "GATE_6B.json", "w", encoding="utf-8") as f:
        json.dump({"gates": gates, "decision": decision, "verdict": verdict,
                   "delta": delta}, f, indent=2, default=str)
    pd.concat(oofs.values(), ignore_index=True).to_parquet(RES6 / "oof6b.parquet")
    manifest = {"seed": SEED, "cost_C": COST_C, "alpha": ALPHA, "n_boot": N_BOOT,
                "cpu_hours": budget["cpu_hours"], "decision": decision, "verdict": verdict,
                "holdout": "UNTOUCHED (P5/B/C/A)"}
    with open(RES6 / "MANIFEST_6B.json", "w", encoding="utf-8") as f:
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
    md.append("# PHASE 6B — RUN REPORT")
    md.append("")
    md.append(f"**Lock:** M20 6B FINAL · **Karar:** {out['verdict']}")
    md.append(f"**CPU:** {out['budget']['cpu_hours']:.3f} / 12 cpu-sa "
              f"({len(out['budget']['ledger'])} fit)")
    md.append("**Koruma:** P5(2025H1)/B(2024H1)/C(2024H2)/A(2023H2) DOKUNULMADI.")
    md.append("")
    md.append("## Veri coverage/hash — MANIFEST_DOWNLOAD_6B.json: 3831 settlement, "
              "2020-01-01 00:00 → 2023-06-30 16:00, max jitter 0.047s, eksik yok; "
              "markPrice EXCLUDED.")
    md.append("## Integrity — monoton+dup+NaN yok; grid aidiyet ±60s; aralik 8h±60s.")
    md.append("## Settlement alignment — ACTUAL ms asof-backward; T candle R(T) gorur, "
              "oncesi gormez (test 12/12).")
    md.append("## Leakage — causality+predicted probe PASS; NEW = 5 kilitli familya; "
              "trailing-only formul testi.")
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
    md.append("## Protected-test verification — TRAIN+VAL loader only; istek penceresi "
              "2020→2023H1 assert'li; holdout verify kosu sonrasi tekrar kosulacak.")
    md.append("## Anomalies — jitter disambiguation (RUN_REPORT notu): 2 settlementte "
              "ms-mertebe jitter (maks 47ms); actual-ms asof ile sizinti yok.")
    md.append("## Exact decision — " + out["verdict"])
    md.append("")
    md.append("**Not:** statistical predictive ≠ economic incremental edge; karar "
              "ekonomik incremental edge uzerinden verildi.")
    with open(A6 / "RUN_REPORT_6B.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    main()