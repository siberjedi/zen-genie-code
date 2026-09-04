"""Phase 3 finalize — TEK SEFER calisir (2026-09-04).

Yapar:
1. Baseline zipleri cozumle (val + 5 CV + Final A) -> bizim metodolojiyle metrikler.
2. Seed sec (SELECTION.md: max validation Sharpe) — Final A'ya bakilmaz.
3. Secilmis dondurulmus modelle Final A TEK degerlendirme (pandas sim).
4. Karsilastirma + istatistik (FDR, paired d/CI, power) + metadata guncelle.

Sonuclara gore config DEGISMEZ. Tekrar calistirmak esit sonuc vermeli
(Final A degerlendirmesi deterministik; yine de TEK SEFER ilkesi gecerli).
"""
import hashlib
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from scripts.phase03_experiment import (metrics_from_trades, simulate, build_panel,
                                        ELIGIBLE_18, MODEL_DIR)
from src.freqai.features import FEATURES
from src.freqai.splits import (slice_frame, VAL_START, VAL_END, FINAL_A_START,
                               FINAL_A_END, SEEDS)
from src.freqai.model import predict_proba
from src.freqai.compare import sharpe_delta, check_thresholds
from src.backtest.evaluate import fdr_correct, cohens_d, compute_power

RES_DIR = ROOT / "experiments" / "phase_03_freqai" / "results"
BT_DIR = ROOT / "freqtrade" / "user_data" / "backtest_results" / "phase03"


def load_baseline():
    """zip -> {key: (trades_df, backtest_start, backtest_end)}."""
    out = {}
    for zp in sorted(BT_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime):
        z = zipfile.ZipFile(zp)
        n = [x for x in z.namelist() if x.endswith(".json") and "config" not in x][0]
        data = json.loads(z.read(n))
        bs = data["strategy"]["BaselineStrategy"]
        out[bs["backtest_start"][:10]] = (pd.DataFrame(bs["trades"]),
                                          bs["backtest_start"], bs["backtest_end"],
                                          bs.get("p_value"))
    return out


def baseline_metrics(trades_df, win_start, win_end):
    recs = trades_df.to_dict("records")
    # zip kolonlari: profit_ratio/profit_abs/open_date/close_date mevcut
    return metrics_from_trades(recs, win_start, win_end)


def daily_abs(trades_df, win_start, win_end):
    df = trades_df.copy()
    df["close_date"] = pd.to_datetime(df["close_date"])
    df["date"] = df["close_date"].dt.date
    s = df.groupby("date")["profit_abs"].sum()
    idx = pd.date_range(win_start, (pd.Timestamp(win_end) - pd.Timedelta(days=1)).date(),
                        freq="D").date
    full = pd.Series(0.0, index=idx)
    full.update(s)
    return full


def main():
    val_m = pd.read_csv(RES_DIR / "val_metrics.csv").sort_values("seed")
    cv_m = pd.read_csv(RES_DIR / "cv_metrics.csv").sort_values("fold")
    base = load_baseline()
    print(f"baseline zipler: {sorted(base.keys())}", flush=True)

    # --- baseline validation + CV (bizim metodoloji) ---
    bval_tr, _, _, bval_p = base["2023-01-01"]
    bval = baseline_metrics(bval_tr, VAL_START, VAL_END)
    print(f"baseline val: trades={bval['trade_count']} net={bval['net_abs']} "
          f"sharpe={bval['daily_sharpe']} dd={bval['max_dd']}", flush=True)

    folds = pd.read_csv(ROOT / "experiments/phase_03_freqai/folds/cv_folds.csv")
    bfold_sharpes, wf_wins = [], []
    fcv = cv_m[cv_m["seed"] == 42].sort_values("fold") if "seed" in cv_m.columns else cv_m
    for _, f in folds.iterrows():
        key = pd.Timestamp(f["test_start"]).strftime("%Y-%m-%d")
        btr, _, _, _ = base[key]
        bm = baseline_metrics(btr, f["test_start"], f["test_end"])
        fm = fcv[fcv["fold"] == int(f["fold"])].iloc[0]
        bfold_sharpes.append(bm["daily_sharpe"])
        wf_wins.append(bool(fm["daily_sharpe"] > bm["daily_sharpe"]))
        print(f"cv fold {int(f['fold'])}: freqai {fm['daily_sharpe']} vs "
              f"baseline {bm['daily_sharpe']} -> {'WIN' if wf_wins[-1] else 'loss'}", flush=True)
    wf_win_rate = sum(wf_wins) / len(wf_wins)

    # --- seed secimi (SADECE validation; Final A'ya bakilmadi) ---
    sel = val_m.loc[val_m["daily_sharpe"].idxmax()]
    sel_seed = int(sel["seed"])
    print(f"selected seed: {sel_seed} (val sharpe {sel['daily_sharpe']})", flush=True)
    seed_std = float(val_m["daily_sharpe"].std(ddof=1))
    delta = sharpe_delta(float(sel["daily_sharpe"]), float(bval["daily_sharpe"]))
    checks = check_thresholds(delta, wf_win_rate, abs(float(sel["max_dd"])), seed_std)
    print(f"delta={delta:.3f} wf_win={wf_win_rate:.2f} dd={sel['max_dd']} "
          f"seed_std={seed_std:.3f} -> {checks['checks']}", flush=True)

    # --- paired istatistik (validation, ayni pencere) ---
    sel_tr = pd.read_csv(RES_DIR / f"val_trades_seed{sel_seed}.csv")
    fa = daily_abs(sel_tr, VAL_START, VAL_END)
    fb = daily_abs(bval_tr, VAL_START, VAL_END)
    assert (fa.index == fb.index).all()
    diff = (fa - fb).values
    from scipy import stats as sstats
    t_res = sstats.ttest_rel(fa.values, fb.values)
    dz = float(diff.mean() / diff.std(ddof=1)) if diff.std(ddof=1) else 0.0
    se = diff.std(ddof=1) / (len(diff) ** 0.5)
    ci = [round(float(diff.mean() - 1.96 * se), 5), round(float(diff.mean() + 1.96 * se), 5)]
    pvals = []
    for s in sorted(val_m["seed"]):
        st = pd.read_csv(RES_DIR / f"val_trades_seed{s}.csv")
        d = (daily_abs(st, VAL_START, VAL_END) - fb).values
        pvals.append(float(sstats.ttest_rel(daily_abs(st, VAL_START, VAL_END).values,
                                            fb.values).pvalue))
    rej, p_corr = fdr_correct(pvals)
    d_ind = cohens_d(fa.values, fb.values)
    pow_req = compute_power(0.30, 176)
    print(f"paired t p={float(t_res.pvalue):.4g} dz={dz:.3f} CI={ci} n={len(diff)}", flush=True)
    print(f"FDR rej {int(sum(rej))}/5 p_corr={[round(float(x),4) for x in p_corr]}", flush=True)

    # --- Final A TEK degerlendirme (dondurulmus model) ---
    import joblib
    model = joblib.load(MODEL_DIR / f"rf_seed{sel_seed}.joblib")
    panel = build_panel(ELIGIBLE_18, end=FINAL_A_END)  # nedensel rolling: sizinti yok
    frames = []
    for pair, df in panel.items():
        s = slice_frame(df, FINAL_A_START, FINAL_A_END)
        if len(s) == 0:
            continue
        # Final A disi dogrulama (guard'in tersi: hepsi ICINDE olmali)
        assert s["date"].min() >= FINAL_A_START and s["date"].max() <= FINAL_A_END
        s = s.copy()
        s["pair"] = pair
        frames.append(s)
    fap = pd.concat(frames, ignore_index=True)
    assert (fap["date"] < FINAL_A_START).sum() == 0, "Final A disi sizdi!"
    Xfa = fap[FEATURES].values
    fap = fap.copy()
    fap["signal"] = [1 if p >= 0.5 else 0 for p in predict_proba(model, Xfa)]
    sig = {}
    for pair, g in fap.groupby("pair"):
        base_df = panel[pair][["date", "open", "high", "low", "close"]].copy()
        mrg = base_df.merge(g[["date", "signal"]], on="date", how="inner")
        mrg = mrg[(mrg["date"] >= FINAL_A_START) &
                  (mrg["date"] <= FINAL_A_END - pd.Timedelta(hours=1))]
        sig[pair] = mrg.sort_values("date").reset_index(drop=True)
    fa_trades, _ = simulate(sig)
    fa_met = metrics_from_trades(fa_trades, FINAL_A_START, FINAL_A_END)
    pd.DataFrame(fa_trades).to_csv(RES_DIR / "final_test_a_trades.csv", index=False)
    bfa_tr, _, _, _ = base["2023-07-01"]
    bfa = baseline_metrics(bfa_tr, FINAL_A_START, FINAL_A_END)
    fa_delta = sharpe_delta(float(fa_met["daily_sharpe"]), float(bfa["daily_sharpe"]))
    print(f"FINAL_A freqai: trades={fa_met['trade_count']} net={fa_met['net_abs']} "
          f"sharpe={fa_met['daily_sharpe']} dd={fa_met['max_dd']}", flush=True)
    print(f"FINAL_A baseline: trades={bfa['trade_count']} net={bfa['net_abs']} "
          f"sharpe={bfa['daily_sharpe']} dd={bfa['max_dd']}", flush=True)
    print(f"FINAL_A delta={fa_delta:.3f} (rapor amacli, tuning YOK)", flush=True)

    # --- kayitlar ---
    fh = hashlib.sha256()
    for p in [ROOT / "src/freqai/features.py", ROOT / "src/freqai/labels.py"]:
        fh.update(p.read_bytes())
    comparison = {
        "selected_seed": sel_seed,
        "selection_rule": "max validation Sharpe (SELECTION.md, pre-results locked)",
        "validation": {int(r["seed"]): {"sharpe": float(r["daily_sharpe"]),
                                        "net": float(r["net_abs"]),
                                        "trades": int(r["trade_count"]),
                                        "max_dd": float(r["max_dd"]),
                                        "win_rate": float(r["win_rate"]),
                                        "profit_factor": float(r["profit_factor"])}
                       for _, r in val_m.iterrows()},
        "seed_stability": {"mean": round(float(val_m['daily_sharpe'].mean()), 3),
                           "median": round(float(val_m['daily_sharpe'].median()), 3),
                           "std": round(seed_std, 3), "threshold": 0.25},
        "baseline_validation": {"sharpe": bval["daily_sharpe"], "net": bval["net_abs"],
                                "trades": bval["trade_count"], "max_dd": bval["max_dd"],
                                "win_rate": bval["win_rate"],
                                "profit_factor": bval["profit_factor"]},
        "delta_vs_baseline": round(delta, 3),
        "threshold_checks": checks,
        "wf_win_rate": {"value": round(wf_win_rate, 3), "wins": [bool(x) for x in wf_wins],
                        "freqai_cv": [float(x) for x in fcv["daily_sharpe"]],
                        "baseline_cv": [float(x) for x in bfold_sharpes]},
        "statistics": {"paired_t_p": float(t_res.pvalue), "cohens_dz_paired": round(dz, 3),
                       "cohens_d_independent": round(float(d_ind), 3),
                       "mean_diff_CI95": ci, "n_days": len(diff),
                       "fdr_rejected": int(sum(rej)), "fdr_p_corr": [round(float(x), 4) for x in p_corr],
                       "power_req_d03": round(float(pow_req), 3),
                       "overlap_note": "ayni pencere (paired); CV foldlari rolling-overlap, bagimsiz degil"},
        "final_test_a": {"freqai": fa_met, "baseline": bfa, "delta": round(fa_delta, 3),
                         "note": "TEK degerlendirme, tuning disi, rapor amacli"},
        "feature_definition_hash": fh.hexdigest()[:16],
    }
    (RES_DIR / "comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    meta_p = ROOT / "experiments/phase_03_freqai/run_metadata.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    import datetime
    meta["status"] = "experiment complete — results locked, no further runs"
    meta["experiment"] = {"executed_at": datetime.datetime.now().astimezone().isoformat(),
                          "git_commit": __import__("subprocess").check_output(
                              ["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                              text=True).strip()}
    meta["results_ref"] = "results/comparison.json"
    meta_p.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("yazildi: comparison.json + run_metadata.json guncellendi", flush=True)


if __name__ == "__main__":
    main()
