"""Phase 5 — Hücre metrikleri + PSS + FDR (4 aile) + arm gates (DESIGN 500 sec 11/12/15/17/22).

Per cell (validation OOF):
- PSS = top-decile mean future return - C ; edge/cost = (mean10 - C)/C
- Sınıflandırma: AUC, PR-AUC, logloss, Brier, ECE(10-bin), directional acc, rank-IC
- Regresyon (L2): R², RMSE, rank-IC
- Decile tablosu: mean/median future return, P(Y>0), P(Y>C), net, edge/cost;
  doğrusal süreklilik: Kendall tau (decile indeks x mean return)
- Cohen d (top vs bottom decile future-return), power (TTestIndPower)
FDR: BH-FDR (benjamini_hochberg, phase418_stats ile AYNI kod), aileler
L0(12) / L1(12) / L2(12) / secondary(8); alpha=0.05.
"""
import math

import numpy as np
import pandas as pd
from scipy import stats as st
from statsmodels.stats.power import TTestIndPower
from sklearn.metrics import (roc_auc_score, average_precision_score, log_loss,
                             mean_squared_error, r2_score, brier_score_loss,
                             accuracy_score)

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase502_labels import COST_C
from phase504_walkforward import WF_MIN_CONSISTENCY

ALPHA = 0.05
POWER = TTestIndPower()
EDGE_MIN = 1.2
AUC_MIN = 0.55
IC_MIN = 0.01
D_MIN = 0.30
POWER_MIN = 0.80
SEED_DIR_MIN = 2 / 3


def benjamini_hochberg(ps):
    """BH-FDR q degerleri — phase418_stats ile ayni kod (kilitli, genisletilmez)."""
    ps = np.asarray(ps, float)
    order = np.argsort(ps)
    qvals = np.empty_like(ps)
    m = len(ps)
    running = 1.0
    for i in np.flip(order):
        running = min(running, ps[i] * m / (i + 1))
        qvals[i] = running
    return [float(x) for x in qvals]


def ece(probas, y, n_bins=10):
    """10-bin calibration error (mean |mean_proba - observed_freq| * bin_weight)."""
    y = np.asarray(y, float)
    p = np.asarray(probas, float)
    idx = np.argsort(p)
    bin_size = max(1, int(np.ceil(len(p) / n_bins)))
    acc = 0.0
    total = 0.0
    for i in range(0, len(p), bin_size):
        chunk = idx[i:i + bin_size]
        if len(chunk) == 0:
            continue
        m_p = p[chunk].mean()
        m_y = y[chunk].mean()
        acc += len(chunk) / len(p) * abs(m_p - m_y)
        total += 1
    return float(acc)


def kendall_decile_order(decile_table):
    """Decile indeks (0..9) x mean future return — Kendall tau."""
    means = [d["mean"] for d in decile_table]
    xs = np.arange(len(means))
    if len(set(means)) < 2:
        return 0.0
    tau, _ = st.kendalltau(xs, means)
    return float(tau) if not np.isnan(tau) else 0.0


def decile_table(scores, future_returns, cost=COST_C, n_buckets=10):
    """Puanina göre onluklar: mean/median future return, P(Y>0), P(Y>C), net, edge/cost.

    En yüksek puan dilimi = true 9 (top decile). n_buckets'ten PD-aktarılmaz.
    """
    s = np.asarray(scores, float)
    r = np.asarray(future_returns, float)
    if len(s) == 0:
        return []
    order = np.argsort(s)
    n = len(s)
    rows = []
    for bi in range(n_buckets):
        lo = bi * n // n_buckets
        hi = (bi + 1) * n // n_buckets
        idx = order[lo:hi]
        if len(idx) == 0:
            continue
        rr = r[idx]
        mean_ret = float(rr.mean())
        rows.append({
            "bucket": bi,
            "mean": mean_ret,
            "median": float(np.median(rr)),
            "p_gt_0": float((rr > 0).mean()),
            "p_gt_C": float((rr > cost).mean()),
            "net": mean_ret - cost,
            "edge_over_cost": (mean_ret - cost) / cost if cost else 0.0,
            "n": int(len(idx)),
        })
    return rows


def pss_stats(scores, future_returns, cost=COST_C, seed=42):
    """PSS + top-decile istatistikleri (hedef: DESIGN sec 11/15/20).

    - scores: tahmin puanı (yüksek = pozitif yön).
    - future_returns: gerçeklesen forward return (Y).
    Dönüş dict: pss, edge_cost, mean10, n_top, cohens_d (top vs bottom), power,
    ci95 (top-decile net premium), p_test (one-sample t, H0: mean10 <= C).
    """
    s = np.asarray(scores, float)
    r = np.asarray(future_returns, float)
    k = max(1, int(np.ceil(len(s) * 0.10)))
    order = np.argsort(-s, kind="stable")
    top = order[:k]
    bot = order[-k:]
    r_top = r[top]
    r_bot = r[bot]
    mean10 = float(r_top.mean())
    pss = mean10 - cost
    edge_cost = pss / cost if cost else 0.0

    # top vs bottom decile future-return Cohen d (DESIGN sec 20, d üzerinden)
    d = _cohens_d(r_top, r_bot)
    power = power_of(d, len(r_top), len(r_bot))
    # one-sample t: H0 mean10 <= C
    diff = r_top - cost
    if diff.std(ddof=1) > 0 and len(diff) > 1:
        tstat, p = st.ttest_1samp(diff, 0.0, alternative="greater")
    else:
        tstat, p = 0.0, 1.0
    # welch CI of top-decile net premium
    mean_net, lo, hi = _welch_ci_onesample(r_top, cost)
    return {
        "pss": float(pss), "edge_over_cost": float(edge_cost),
        "mean10": mean10, "n_top": int(k),
        "cohens_d": round(float(d), 4),
        "power": round(float(power), 3),
        "t": float(tstat), "p_test": float(p),
        "ci95_net": [round(lo, 8), round(hi, 8)],
        "pss_positive": bool(pss > 0),
        "edge_ge_1.2": bool(edge_cost >= EDGE_MIN),
    }


def _cohens_d(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n1 = len(x)
    n2 = len(y)
    if min(n1, n2) < 2:
        return 0.0
    pooled = math.sqrt(((n1 - 1) * x.std(ddof=1) ** 2
                        + (n2 - 1) * y.std(ddof=1) ** 2) / (n1 + n2 - 2))
    return float((x.mean() - y.mean()) / pooled) if pooled > 0 else 0.0


def power_of(d, n1, n2, alpha=ALPHA):
    if d == 0 or min(n1, n2) < 2:
        return 0.0
    if abs(d) >= 1.5:
        return 1.0  # cok buyuk etki -> noncentral-t kuantili numerik NaN uretir, power~1
    return float(POWER.power(effect_size=abs(d), nobs1=min(n1, n2),
                             alpha=alpha, ratio=1.0))


def _welch_ci_onesample(x, null, alpha=ALPHA):
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return np.nan, np.nan, np.nan
    m = x.mean() - null
    se = x.std(ddof=1) / math.sqrt(n)
    tc = st.t.ppf(1 - alpha / 2, n - 1)
    return float(m), float(m - tc * se), float(m + tc * se)


def cell_metrics(scores, y_label, future_returns, label, block, model, cost=COST_C,
                 seed=42, cell_id=""):
    """Bir cell için TÜM metrikleri toplar. (results) dict döndürür."""
    s = np.asarray(scores, float)
    y = np.asarray(y_label, float)
    r = np.asarray(future_returns, float)
    out = {
        "cell_id": cell_id, "block": block, "label": label, "model": model,
        "n_val": int(len(s)),
    }
    if label in ("L0", "L1"):
        mask = ~np.isnan(y)
        if mask.sum() > 1 and len(set(y[mask])) > 1:
            out["auc"] = float(roc_auc_score(y[mask], s[mask]))
            out["pr_auc"] = float(average_precision_score(y[mask], s[mask]))
            out["logloss"] = float(log_loss(y[mask], np.clip(s[mask], 1e-9, 1 - 1e-9)))
            out["brier"] = float(brier_score_loss(y[mask], np.clip(s[mask], 0, 1)))
            out["ece"] = ece(s[mask], y[mask], 10)
            out["dir_acc"] = float(accuracy_score(y[mask], (s[mask] >= 0.5).astype(int)))
            if len(set(s[mask])) > 1:
                ic, _ = st.spearmanr(s[mask], r[mask])
                out["rank_ic"] = float(ic) if not np.isnan(ic) else 0.0
            else:
                out["rank_ic"] = 0.0
        else:
            for k in ("auc", "pr_auc", "logloss", "brier", "ece", "dir_acc", "rank_ic"):
                out[k] = 0.0
    else:  # L2 regression
        out["rmse"] = float(np.sqrt(mean_squared_error(y, s)))
        out["r2"] = float(r2_score(y, s)) if len(set(y)) > 1 else 0.0
        if len(set(s)) > 1:
            ic, _ = st.spearmanr(s, r)
            out["rank_ic"] = float(ic) if not np.isnan(ic) else 0.0
        else:
            out["rank_ic"] = 0.0
    out["deciles"] = decile_table(s, r, cost)
    out["kendall_tau"] = kendall_decile_order(out["deciles"])
    out["pss"] = pss_stats(s, r, cost, seed)
    return out


def fdr_family(cells, family_name):
    """Bir ailedeki p degerleri üzerinden BH-FDR. (fdr) üretir."""
    ps = [c["pss"]["p_test"] for c in cells]
    qs = benjamini_hochberg(ps) if ps else []
    for c, q in zip(cells, qs):
        c["pss"]["q"] = round(float(q), 4)
    n_sig = sum(1 for q in qs if q < ALPHA) if qs else 0
    return {"family": family_name, "n_cells": len(cells),
            "n_q_lt_alpha": n_sig, "cells": cells}


def arm_gate(fdr_cells, family_name):
    """DESIGN sec 22 arm gate. (dict) PASS/FAIL + neden."""

    def _goal(_c):
        return _c["pss"]

    sig = [c for c in fdr_cells["cells"] if c["pss"].get("q", 1) < ALPHA]
    blocks = sorted({c["block"] for c in sig})
    models = sorted({c["model"] for c in sig})
    cond_a = (len(sig) >= 1 and len(blocks) >= 2 and len(models) >= 2)
    cond_b_cells = [c for c in sig
                    if (c.get("auc", 0) >= AUC_MIN if "auc" in c else False)
                    and c.get("rank_ic", 0) >= IC_MIN and c.get("kendall_tau", 0) > 0]

    def _cond_b(c):
        if "auc" in c:
            base = c["auc"] >= AUC_MIN
        else:
            base = c["r2"] > 0  # L2 regresyon: destek olarak pozitif R2 (rapor)
        return base and c.get("rank_ic", 0) >= IC_MIN and c.get("kendall_tau", 0) > 0

    cond_b = [c for c in sig if _cond_b(c)]
    cond_bool = len(cond_b) >= 1
    cond_c = [c for c in cond_b if c["pss"]["pss_positive"] and c["pss"]["edge_ge_1.2"]]
    cond_d = [c for c in cond_c if c["pss"]["cohens_d"] >= D_MIN
              and c["pss"]["power"] >= POWER_MIN]
    passed = len(cond_d) >= 1
    return {
        "family": family_name,
        "gate_pass": bool(passed),
        "a_ge2block_ge2model": bool(cond_a),
        "b_support": bool(cond_bool),
        "b_detail": {"cells": [c["cell_id"] for c in cond_b],
                     "n_support": len(cond_b)},
        "c_pss_edge": bool(len(cond_c) >= 1),
        "d_d_power": bool(len(cond_d) >= 1),
        "candidate_cells": [c["cell_id"] for c in cond_d],
        "blocks_fdr": blocks, "models_fdr": models,
        "n_fdr_sig": len(sig),
    }


def select_candidate(arm_gates, all_cells):
    """Frozen tek kural: gate'ten gecen TÜM hücreler içinde argmax(edge/cost);
    tie-break düşük cell id. (candidate_id) döndürür (yoksa None)."""
    cands = []
    for g in arm_gates:
        if not g["gate_pass"]:
            continue
        for cell_id in g["candidate_cells"]:
            c = next(x for x in all_cells if x["cell_id"] == cell_id)
            cands.append((c["pss"]["edge_over_cost"], cell_id))
    if not cands:
        return None
    cands.sort(key=lambda t: (-t[0], t[1]))
    return cands[0][1]


def seed_direction_consistency(candidate_id, seed_runs):
    """3 seed ({42,7,123}) PSS işareti >= 2/3 ayni yönde olmali. dict döndürür."""
    signs = []
    for seed, res in seed_runs.items():
        if candidate_id in res:
            signs.append(1 if res[candidate_id]["pss"] > 0 else 0)
    if not signs:
        return {"evaluable": False, "frac": 0.0}
    frac = sum(signs) / len(signs)
    return {"evaluable": True, "frac": round(frac, 3),
            "pass": bool(frac >= SEED_DIR_MIN),
            "signs": signs, "n": len(signs)}


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    s = rng.normal(0, 1, 1000)
    y = (s + rng.normal(0, 1, 1000) > 0).astype(float)
    r = 0.01 * (s + rng.normal(0, 1, 1000)) + 0.001
    m = cell_metrics(s, y, r, "L1", "B0", "M3", cell_id="E001")
    print("cell_metrics.keys:", sorted(k for k in m if k != "deciles"))
    print("PSS:", m["pss"])
    print("auc=%.3f rank_ic=%.3f tau=%.3f" % (m["auc"], m["rank_ic"], m["kendall_tau"]))
    ps = [0.01, 0.04, 0.03, 0.4, 0.2, 0.05]
    print("BH:", benjamini_hochberg(ps))