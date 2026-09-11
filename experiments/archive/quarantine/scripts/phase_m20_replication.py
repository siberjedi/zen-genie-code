"""M.20 lower-cost execution replication — PURE RECOMPUTATION (fit YOK).

Girdiler (kilitli artefaktlar, degistirilmez):
- results7/oof7.parquet: date/score/future_return/event (647 event, H48 M2 s42)
- 6B funding_btcusdt.parquet: funding_ms/funding_rate (3831 settlement)
- RESULTS_7.json: q90, lambda kaynagi (event sayisi)

Maliyet (frozen, externally justified — optimize YOK):
- commission = 2 x 0.0004 (Binance USDs-M regular taker, donem-belgeli 0.04%)
- spread/slippage = 0.0010 (Phase 8 muhafazakar: 5bps/side)
- funding_i = LONG icin (t_i, t_i+48bar] settlement oranlari toplami (6B verisi)
- C_M20_fixed = 0.0018 ; toplam_i = 0.0018 + funding_i

Cikti: M.20 metrikleri + karsilastirma tablosu (stdout JSON).
Model fit YOK, sklearn YOK, holdout YOK.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as st

ROOT = Path(__file__).resolve().parents[1]
R7 = ROOT / "experiments" / "phase_07_horizon" / "results7"
FB = ROOT / "experiments" / "phase_06_market_context" / "6B_funding" / "data"

COMMISSION_RT = 0.0008   # 2 x 0.0004 regular taker (donem-belgeli)
SLIP_RT = 0.0010         # Phase 8 muhafazakar 5bps/side
C_FIXED = COMMISSION_RT + SLIP_RT
HOLD_MS = 48 * 5 * 60 * 1000
ALPHA = 0.05


def main():
    oof = pd.read_parquet(R7 / "oof7.parquet")
    fund = pd.read_parquet(FB / "funding_btcusdt.parquet").sort_values("funding_ms")
    fms = fund["funding_ms"].to_numpy(dtype="int64")
    frt = fund["funding_rate"].to_numpy(dtype=float)

    s = oof["score"].to_numpy(float)
    Y = oof["future_return"].to_numpy(float)
    dts = pd.to_datetime(oof["date"])
    if getattr(dts.dt, "tz", None) is None:
        dts = dts.dt.tz_localize("UTC")
    tms = ((dts - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta("1ms")).to_numpy()
    ev = oof["event"].to_numpy(bool)
    assert int(ev.sum()) == 647, f"event seti degismis: {int(ev.sum())}"

    # --- per-event funding (LONG: oran pozitifse oder) ---
    t_ev = tms[ev]
    need_max = (t_ev + HOLD_MS).max()
    assert need_max <= fms.max(), \
        f"STOP: funding kapsama disi (need={need_max} > max={fms.max()})"
    fund_i = np.array([frt[(fms > t) & (fms <= t + HOLD_MS)].sum() for t in t_ev])
    cost_i = C_FIXED + fund_i

    r_new = Y[ev] - cost_i          # M.20 net event getirisi
    gross = float(Y[ev].mean())     # M.20 gross (Phase 7 event-gross ile ayni olmali)
    net = float(r_new.mean())
    lam = len(r_new) * 365.0 / 181
    mu, sd = r_new.mean(), r_new.std(ddof=1)
    theta = float(mu / sd * np.sqrt(lam))
    # block bootstrap CI (K=500 event, 10k, s42 — DESIGN_700 aynisi)
    rng = np.random.default_rng(42)
    n, K = len(r_new), 500
    outs = np.empty(10000)
    for b in range(10000):
        st_ = rng.integers(0, n - K + 1, int(np.ceil(n / K)))
        idx = np.concatenate([np.arange(x, x + K) for x in st_])[:n]
        sm = r_new[idx]
        outs[b] = sm.mean() / sm.std(ddof=1) * np.sqrt(lam)
    lo, hi = np.nanpercentile(outs, [2.5, 97.5])
    eq = np.cumsum(r_new)
    maxdd = float(-(eq - np.maximum.accumulate(eq)).min())
    downside = r_new[r_new < 0]
    sortino = float(r_new.mean() / downside.std(ddof=1) * np.sqrt(lam)) if len(downside) > 1 else 0.0
    g, l = r_new[r_new > 0].sum(), -r_new[r_new < 0].sum()

    # --- pooled-decile cercevesi (C_M20_mean ile; sureklilik) ---
    k = int(np.ceil(len(s) * 0.10))
    top = np.argsort(-s, kind="stable")[:k]
    # decile uyeleri icin de per-row funding (ayni deterministik kural)
    t_top = tms[top]
    fund_top = np.array([frt[(fms > t) & (fms <= t + HOLD_MS)].sum() for t in t_top])
    net_top = Y[top] - (C_FIXED + fund_top)
    pss_m = float(net_top.mean())
    c_mean = float(C_FIXED + fund_top.mean())
    edge_m = float(pss_m / c_mean)
    diff = net_top - 0.0
    tstat, pval = (st.ttest_1samp(diff, 0.0, alternative="greater")
                   if diff.std(ddof=1) > 0 else (0.0, 1.0))
    # Cohen d top-vs-bottom (cost-free, degismemeli)
    bot = np.argsort(-s, kind="stable")[-k:]
    rt, rb = Y[top], Y[bot]
    import math
    pooled = math.sqrt(((len(rt)-1)*rt.std(ddof=1)**2 + (len(rb)-1)*rb.std(ddof=1)**2) / (len(rt)+len(rb)-2))
    d = float((rt.mean() - rb.mean()) / pooled) if pooled > 0 else 0.0

    out = {
        "C_M20_fixed": C_FIXED, "commission_rt": COMMISSION_RT, "slip_rt": SLIP_RT,
        "funding_mean_event": round(float(fund_i.mean()), 8),
        "funding_min_event": round(float(fund_i.min()), 8),
        "funding_max_event": round(float(fund_i.max()), 8),
        "C_M20_mean_total": round(float(cost_i.mean()), 8),
        "phase7_gross_pooled": round(0.002341, 8),
        "phase7_net_pooled_C0003": round(0.002341 - 0.003, 8),
        "m20_gross_event": round(gross, 8),
        "m20_net_event": round(net, 8),
        "C_break_even_event": round(gross, 8),
        "safety_margin": round(gross - float(cost_i.mean()), 8),
        "theta": round(theta, 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
        "maxdd": round(maxdd, 4), "sortino": round(sortino, 4),
        "profit_factor": round(float(g / l), 4) if l > 0 else None,
        "win_rate": round(float((r_new > 0).mean()), 4),
        "n_events": int(len(r_new)),
        "pss_pooled": round(pss_m, 8), "edge_pooled": round(edge_m, 4),
        "p_test_pooled": float(pval), "cohens_d": round(d, 4),
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
