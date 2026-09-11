"""Phase 4.18 - Statistics: per-seed tests, MC p, MWU/Welch, effect sizes,
power, FDR, pooled seed-cluster bootstrap, edge decision.

PRIMARY: per-seed BUY forward return h=12, RL vs random/control, 2000 MC rep.
- n < 12        -> "EVALUABLE DEGIL" (edge lehine yorumlanmaz)
- power < 0.80  -> "LOW POWER"
- pooledt: seed bagimsizligi VARSAYILMAZ (seed-cluster bootstrap, 10000 vs, CI).

Cikti: tuning47/stats418.json
Calistir: py -3 scripts/phase418_stats.py
"""
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from scipy import stats as st
from statsmodels.stats.power import TTestIndPower

D47 = ROOT / "experiments" / "phase_04_rl" / "tuning47"
SEEDS = [42, 7, 123, 2026, 999]
HORIZONS = [1, 3, 12, 36, 72, 240, 720]
PRIMARY_H = 12
N_REP = 2000
EVALUABLE_MIN = 12
ALPHA = 0.05
POWER_TARGET = 0.80
THRESHOLDS = [0.002, 0.004, 0.008]
POWER = TTestIndPower()


def cliff_delta(x, y):
    """Cliff's delta (unpaired). x,y arrays."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    n1, n2 = len(x), len(y)
    u = st.mannwhitneyu(x, y, alternative="two-sided").statistic
    return float(2.0 * u / (n1 * n2) - 1.0)


def welch_df(s1, n1, s2, n2):
    den = (s1 ** 2 / n1) ** 2 / (n1 - 1) + (s2 ** 2 / n2) ** 2 / (n2 - 1)
    if den <= 0:
        return 1.0
    return (s1 ** 2 / n1 + s2 ** 2 / n2) ** 2 / den


def welch_ci(x, y, alpha=ALPHA):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m1, m2 = x.mean(), y.mean()
    s1, s2 = x.std(ddof=1), y.std(ddof=1)
    n1, n2 = len(x), len(y)
    df = welch_df(s1, n1, s2, n2)
    se = math.sqrt(s1 ** 2 / n1 + s2 ** 2 / n2)
    tc = st.t.ppf(1 - alpha / 2, df)
    return m1 - m2, (m1 - m2) - tc * se, (m1 - m2) + tc * se


def cohens_d(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    n1, n2 = len(x), len(y)
    pooled = math.sqrt(((n1 - 1) * x.std(ddof=1) ** 2 + (n2 - 1) * y.std(ddof=1) ** 2)
                       / (n1 + n2 - 2))
    return float((x.mean() - y.mean()) / pooled) if pooled > 0 else 0.0


def power_of(d, n1, n2, alpha=ALPHA):
    if d == 0 or min(n1, n2) < 2:
        return 0.0
    return float(POWER.power(effect_size=abs(d), nobs1=min(n1, n2),
                             alpha=alpha, ratio=1.0))


def bootstrap_mean_diff_ci(x, y, rng, n_iter=2000, alpha=ALPHA):
    x, y = np.asarray(x, float), np.asarray(y, float)
    diffs = np.empty(n_iter)
    for b in range(n_iter):
        sx = x[rng.integers(0, len(x), size=len(x))]
        sy = y[rng.integers(0, len(y), size=len(y))]
        diffs[b] = sx.mean() - sy.mean()
    lo = np.percentile(diffs, 100 * alpha / 2)
    hi = np.percentile(diffs, 100 * (1 - alpha / 2))
    return lo, hi


def benjamini_hochberg(ps):
    ps = np.asarray(ps, float)
    order = np.argsort(ps)
    qvals = np.empty_like(ps)
    m = len(ps)
    running = 1.0
    for i in np.flip(order):
        running = min(running, ps[i] * m / (i + 1))
        qvals[i] = running
    return [float(x) for x in qvals]


def cluster_bootstrap_ci(seed_diffs, rng, iters=10000, alpha=ALPHA):
    """Seed-cluster bootstrap CI der magic: event bagimsizligi VARSAYILMAZ."""
    keys = sorted(seed_diffs.keys())
    values = np.asarray([seed_diffs[k] for k in keys], dtype=float)
    boots = np.empty(iters)
    for b in range(iters):
        pick = rng.integers(0, len(keys), size=len(keys))
        boots[b] = values[pick].mean()
    lo = np.percentile(boots, 100 * alpha / 2)
    hi = np.percentile(boots, 100 * (1 - alpha / 2))
    return float(values.mean()), float(lo), float(hi)


def cell_tests(rl_vals, ctrl_rep_mean, ctrl_rep_med, ctrl_rep0, kind, rng):
    rl = np.asarray(rl_vals, dtype=float)
    ctrl = np.asarray(ctrl_rep0, dtype=float)
    n = len(rl)
    rl_mean, rl_med = float(rl.mean()), float(np.median(rl))
    if kind == "buy":
        mc_p_mean = float((ctrl_rep_mean >= rl_mean).mean())
        mc_p_med = float((ctrl_rep_med >= rl_med).mean())
    else:  # sell: daha dusuk (negatif) iyidir
        mc_p_mean = float((ctrl_rep_mean <= rl_mean).mean())
        mc_p_med = float((ctrl_rep_med <= rl_med).mean())
    mwu = st.mannwhitneyu(rl, ctrl, alternative="two-sided")
    welch = st.ttest_ind(rl, ctrl, equal_var=False)
    d = cohens_d(rl, ctrl)
    cliff = cliff_delta(rl, ctrl)
    pw = power_of(d, n, len(ctrl))
    dmean, ci_lo, ci_hi = welch_ci(rl, ctrl)
    lo_b, hi_b = bootstrap_mean_diff_ci(rl, ctrl, rng)
    frac = float((rl > 0).mean()) if kind == "buy" else float((rl < 0).mean())
    binom_p = st.binomtest(int(round(frac * n)), n, 0.5,
                           alternative="two-sided").pvalue if n else 1.0
    hits = {f"r>{t}": {"rl": float((rl > t).mean()),
                       "ctrl_r0": float((ctrl > t).mean())} for t in THRESHOLDS}
    evaluable = n >= EVALUABLE_MIN
    low_power = pw < POWER_TARGET
    return {"n": int(n), "kind": kind, "rl_mean": round(rl_mean, 8),
            "rl_median": round(rl_med, 8),
            "ctrl_mean_med": round(float(np.median(ctrl_rep_mean)), 8),
            "ctrl_med_med": round(float(np.median(ctrl_rep_med)), 8),
            "mc_p_mean": round(mc_p_mean, 4), "mc_p_median": round(mc_p_med, 4),
            "mwu_u": float(mwu.statistic), "mwu_p": float(mwu.pvalue),
            "welch_t": float(welch.statistic), "welch_p": float(welch.pvalue),
            "mean_diff": round(dmean, 8), "ci95_mean_diff": [round(ci_lo, 8),
                                                            round(ci_hi, 8)],
            "ci95_mean_diff_boot": [round(lo_b, 8), round(hi_b, 8)],
            "cohens_d": round(d, 4), "cliff_delta": round(cliff, 4),
            "power": round(pw, 3),
            "directional": {"frac": round(frac, 4),
                            "p_binom_vs_0p5": round(float(binom_p), 4)},
            "threshold_hits": hits,
            "evaluable": bool(evaluable), "flag": "EVALUABLE DEGIL" if not evaluable else
            ("LOW POWER" if low_power else "OK")}


def pooled_gates(events, fwd, kind="buy"):
    ev_seeds = [s for s in SEEDS
                if events["seeds"][str(s)][f"n_{kind}_h"][str(PRIMARY_H)] > 0]
    diffs = {}
    for s in ev_seeds:
        evs = events["seeds"][str(s)]["buys"] if kind == "buy" \
            else events["seeds"][str(s)]["sells"]
        hs = str(PRIMARY_H)
        rl = np.asarray([e["r"][hs] for e in evs.values() if hs in e["r"]])
        cmed = np.asarray(fwd[f"control_{kind}"][str(s)][hs]["ctrl_median_rep"])
        diffs[str(s)] = float(np.median(rl) - np.median(cmed))
    rng = np.random.default_rng(41818)
    iters = 10000
    metric, lo, hi = cluster_bootstrap_ci(diffs, rng, iters)
    return {"kind": kind, "seeds_used": ev_seeds,
            "per_seed_median_diff": {k: round(v, 8) for k, v in diffs.items()},
            "metric_mean_of_seed_median_diffs": round(metric, 8),
            "ci95_cluster_boot": [round(float(lo), 8), round(float(hi), 8)],
            "lower_gt_0": bool(lo > 0),
            "note": "seed cluster bootstrap (10000, seed bazinda ornekleme) - "
                    "event bagimsizligi VARSAYILMAZ"}


def main():
    events = json.load(open(D47 / "events418.json", encoding="utf-8"))
    fwd = json.load(open(D47 / "forward418.json", encoding="utf-8"))
    if not events["meta"]["leakage_audit"]["passed"]:
        print("Leakage audit FAILED -> istatistik calistirilmaz."); sys.exit(1)

    primary = {"buy": {}, "sell": {}}
    secondary = {"buy": {}, "sell": {}}
    mc_ps_buy_h12 = {}

    for s in SEEDS:
        for kind in ("buy", "sell"):
            evs = events["seeds"][str(s)]["buys"] if kind == "buy" \
                else events["seeds"][str(s)]["sells"]
            block_fwd = fwd[f"control_{kind}"][str(s)]
            rng = np.random.default_rng(41900 + s + (0 if kind == "buy" else 1))
            for h in HORIZONS:
                hs = str(h)
                cell = block_fwd[hs]
                n = cell.get("n", 0)
                if n == 0:
                    sec = secondary[kind].setdefault(str(s), {})
                    sec[hs] = {"n": 0}
                    continue
                rl = np.asarray([e["r"][hs] for e in evs.values() if hs in e["r"]])
                cmean = np.asarray(cell["ctrl_mean_rep"])
                cmed = np.asarray(cell["ctrl_median_rep"])
                rep0 = np.asarray(cell["ctrl_sample_rep0"])
                res = cell_tests(rl, cmean, cmed, rep0, kind, rng)
                if h == PRIMARY_H:
                    primary[kind][str(s)] = res
                    if kind == "buy":
                        mc_ps_buy_h12[str(s)] = res["mc_p_mean"]
                else:
                    sec = secondary[kind].setdefault(str(s), {})
                    sec[hs] = res
        if "buy" not in primary:  # 2026 no-p data placeholder (karsilastirma tablosu icin)
            pass

    # FDR (BUY h12) BH
    sig_seeds = [s for s in SEEDS if str(s) in mc_ps_buy_h12]
    ps = [mc_ps_buy_h12[str(s)] for s in sig_seeds]
    qs = benjamini_hochberg(ps) if ps else []
    fdr = {str(s): round(q, 4) for s, q in zip(sig_seeds, qs)}

    pooled_buy = pooled_gates(events, fwd, "buy")
    pooled_sell = pooled_gates(events, fwd, "sell")

    # control sanity (F3d)
    drift12 = fwd["drift_h"]["12"]
    fa_ok = all(fwd["freqai_buy"][str(s)]["status"] == "ok" for s in SEEDS)
    sanity = {"drift_h12_positive": drift12 > 0, "freqai_ok": bool(fa_ok),
              "all_pass": drift12 > 0 and bool(fa_ok)}

    # edge decision (preregistered F3)
    evaluable_ok = [s for s in ("42", "7", "123", "999") if str(s) in fdr]
    min_q = min([fdr[s] for s in evaluable_ok]) if evaluable_ok else 1.0
    directed = sum(1 for s in pooled_buy["per_seed_median_diff"]
                   if pooled_buy["per_seed_median_diff"][s] > 0)
    n_sig = len(pooled_buy["per_seed_median_diff"])
    c1 = pooled_buy["lower_gt_0"]
    c2 = min_q < ALPHA
    c3 = directed >= 3 and n_sig >= 3
    c4 = sanity["all_pass"]
    verdict = all([c1, c2, c3, c4])
    edge = {"conditions": {"C1_pooled_lower_CI_gt_0": bool(c1),
                           "C2_bh_q_lt_0.05": bool(c2),
                           "C3_ge_3of5_seeds_same_dir": bool(c3),
                           "C4_control_sanity": bool(c4),
                           "detail": {"min_q": round(min_q, 4),
                                      "directed_seeds": directed, "n_signal_seeds": n_sig}},
            "verdict_decision_level_buy_edge": bool(verdict),
            "note": "2026 (0 BUY) edge-yok kaniti OLARAK KULLANILMAZ; "
                    "7/999 n<12 -> EVALUABLE DEGIL (edge lehine sayilmaz).",
            "final_answer_A": "DECISION-LEVEL EDGE" if verdict
            else "DECISION-LEVEL EDGE YOK"}

    out = {"primary_h": PRIMARY_H, "evaluable_min": EVALUABLE_MIN,
           "power_target": POWER_TARGET, "n_rep": N_REP,
           "primary": primary, "secondary_horizons": secondary,
           "fdr_buy_h12_bh": fdr, "sanity": sanity,
           "pooled_buy": pooled_buy, "pooled_sell": pooled_sell,
           "edge_decision": edge,
           "final_A_B_C": {"A_pred_power": edge["final_answer_A"],
                           "B_econ": "Ekonomik edge (P&L/Sharpe) BU FAZIN RESMI "
                                     "SONUCU DEGIL; E1 locked A-gate 4.17'de FAIL "
                                     "(0.225<0.80) idi.",
                           "C_drift": "4.16/4.17: RL ≈ exposure × drift; bu fazin "
                                     "decision-level bulgusu A ile birlikte raporlanir."}}
    json.dump(out, open(D47 / "stats418.json", "w", encoding="utf-8"), indent=2, default=str)

    print("== PRIMARY BUY h=12 (RL vs random/control) ==")
    for s in SEEDS:
        r = primary["buy"].get(str(s))
        if not r:
            print(f"  seed {s:>4}: n=0 (sinyal yok)"); continue
        print(f"  seed {s:>4}: n={r['n']:>3} flag={r['flag']:<16} rl_mean={r['rl_mean']:+.6f} "
              f"rl_med={r['rl_median']:+.6f} ctrl_med={r['ctrl_med_med']:+.6f} "
              f"mc_p_mean={r['mc_p_mean']:.4f} mwu_p={r['mwu_p']:.4f} d={r['cohens_d']:+.3f} "
              f"pw={r['power']:.2f} dir={r['directional']['frac']:.2f}")
    print("== PRIMARY SELL h=12 ==")
    for s in SEEDS:
        r = primary["sell"].get(str(s))
        if not r:
            print(f"  seed {s:>4}: n=0"); continue
        print(f"  seed {s:>4}: n={r['n']:>3} flag={r['flag']:<16} rl_mean={r['rl_mean']:+.6f} "
              f"rl_med={r['rl_median']:+.6f} ctrl_med={r['ctrl_med_med']:+.6f} "
              f"mc_p_mean={r['mc_p_mean']:.4f} dir_neg={r['directional']['frac']:.2f}")
    print("FDR (BUY h12):", fdr)
    print("Pooled BUY:", pooled_buy)
    print("Pooled SELL:", pooled_sell)
    print("Sanity:", sanity)
    print("Edge:", edge)
    print("\nstats418.json yazildi:", D47 / "stats418.json")


if __name__ == "__main__":
    main()