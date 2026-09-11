"""Phase 4.18 - Forward returns + random/control MC + B&H/drift + FreqAI refs.

"RL BUY forward return vs AYNI KOSULLARDAN random/control" calistirir (2000 MC rep).
- Rejim eslemesi: seed'in her rejimdeki BUY sayisi kadar, AYNI rejim step havuzundan
  uniform random giris; ayni h ufuklari.
- Trend-aware: yukselen pencerede herhangi bir noktadan random girisin pozitif
  olmasi artefaktini RL'den ayirir.
- MC deterministik (numpy Generator, seed = 418000 + h*100 + seed + kind_flag).
- FreqAI: val_trades_seed{s}.csv -> pair BTC/USDT -> entry indeksleri -> ayni r_h.
- Phase3 baseline: per-entry artefact YOK (comparison.json metrics-only) -> N/A.

Cikti: tuning47/forward418.json
Calistir: py -3 scripts/phase418_forward.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from scripts.phase416_drift import candle_regimes, load_val, simulate

D47 = ROOT / "experiments" / "phase_04_rl" / "tuning47"
P3 = ROOT / "experiments" / "phase_03_freqai" / "results"
SEEDS = [42, 7, 123, 2026, 999]
HORIZONS = [1, 3, 12, 36, 72, 240, 720]
PRIMARY_H = 12
N_REP = 2000
N_TRADABLE = 51794


def eligible_steps(creg, h, regime=None, exec_off=30):
    """k in [0, N_TRADABLE); creg[30+k]==regime (esitse); 30+k+h <= len(closes)-1."""
    n = len(creg)
    return np.asarray([k for k in range(N_TRADABLE)
                       if (exec_off + k + h) <= n - 1
                       and (regime is None or creg[exec_off + k] == regime)],
                      dtype=int)


def draws_at(closes, creg, ks, h, exec_off=30):
    return np.asarray([closes[exec_off + k + h] / closes[exec_off + k] - 1.0
                       for k in ks], dtype=float)


def mc_control(closes, creg, regime_counts, h, n_rep, rng, exec_off=30):
    """random/control: counts (regime->n) kadar AYNI rejim havuzundan cekim.
    Donar: (ctrl_mean_rep[n_rep], ctrl_median_rep[n_rep], rep0_sample[n])."""
    pools = {r: draws_at(closes, creg, eligible_steps(creg, h, r, exec_off), h, exec_off)
             for r in regime_counts if regime_counts[r] > 0}
    means, medians = np.empty(n_rep), np.empty(n_rep)
    rep0 = None
    for rep in range(n_rep):
        vecs = []
        for r in sorted(regime_counts):
            cnt = regime_counts[r]
            if cnt <= 0:
                continue
            pool = pools[r]
            assert len(pool) >= cnt, (r, h, len(pool), cnt)
            vecs.append(pool[rng.integers(0, len(pool), size=cnt)])
        v = np.concatenate(vecs)
        means[rep], medians[rep] = v.mean(), np.median(v)
        if rep == 0:
            rep0 = v
    return means, medians, np.asarray(rep0, dtype=float)


def regime_key(seed, h, kind):
    return 418000 + h * 100 + seed + (0 if kind == "buy" else 1)


def drift_h(closes, h, exec_off=30):
    n = len(closes)
    vals = [closes[exec_off + k + h] / closes[exec_off + k] - 1.0
            for k in range(N_TRADABLE) if exec_off + k + h <= n - 1]
    return float(np.mean(vals))


def bh_refs(closes):
    gross = float(closes[-1] / closes[30] - 1.0)
    act = ["B"] + [None] * (len(closes) - 1 - 30)
    tr, pre, _ = simulate(act, closes)
    net = float(sum(t["profit"] for t in tr) / 100.0)
    return {"gross_pct": round(gross * 100.0, 3), "net_pct": round(net * 100.0, 3),
            "n_trades": len(tr)}


def freqai_events(seed, closes, date2idx):
    """val_trades_seed{s}.csv -> BTC/USDT rows -> val indeksleri -> r_h per entry."""
    fp = P3 / f"val_trades_seed{seed}.csv"
    if not fp.exists():
        return {"status": "missing_file", "n_entries": 0, "unmatched": 0,
                "entries": [], "n_h": {}, "mean_h": {}, "median_h": {}}
    df = pd.read_csv(fp)
    df = df[df["pair"] == "BTC/USDT"].reset_index(drop=True)
    opens = pd.to_datetime(df["open_date"]).dt.tz_localize(None)\
            .dt.strftime("%Y-%m-%d %H:%M:%S")
    entries, unmatched = [], 0
    for i in range(len(opens)):
        b = date2idx.get(str(opens.iloc[i]))
        if b is None or b < 30:
            unmatched += 1
            continue
        r = {}
        for h in HORIZONS:
            if b + h <= len(closes) - 1:
                r[str(h)] = float(closes[b + h] / closes[b] - 1.0)
        entries.append({"idx": int(b), "r": r})
    n_h = {str(h): sum(1 for e in entries if str(h) in e["r"]) for h in HORIZONS}
    return {"status": "ok", "n_entries": len(entries), "unmatched": unmatched,
            "entries": entries, "n_h": n_h,
            "mean_h": {str(h): round(float(np.mean([e["r"][str(h)] for e in entries
                                                    if str(h) in e["r"]])), 6)
                       if n_h[str(h)] else None for h in HORIZONS},
            "median_h": {str(h): round(float(np.median([e["r"][str(h)] for e in entries
                                                        if str(h) in e["r"]])), 6)
                         if n_h[str(h)] else None for h in HORIZONS}}


def main():
    full, vdf = load_val()
    closes = vdf["close"].values.astype(float)
    creg = candle_regimes(full, vdf.copy())

    ds = pd.to_datetime(vdf["date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    date2idx = {str(x): int(i) for i, x in enumerate(ds)}

    events = json.load(open(D47 / "events418.json", encoding="utf-8"))
    if not events["meta"]["leakage_audit"]["passed"]:
        print("Leakage audit FAILED -> forward analizi calistirilmaz.")
        sys.exit(1)

    out = {"buy_hold": bh_refs(closes),
           "drift_h": {str(h): round(drift_h(closes, h), 6) for h in HORIZONS},
           "control_buy": {}, "control_sell": {}, "regime_buy": {},
           "freqai_buy": {}, "phase3_baseline": {
               "status": "N/A",
               "reason": "Phase 3 baseline per-entry trade artefacti yok "
                         "(comparison.json metrics-only); Gameplan baseline "
                         "≈ buy-and-hold -> B&H satirina yonlendirildi."},
           "mc": {"n_rep": N_REP, "seed_formula": "418000 + h*100 + seed + kind",
                  "kind_flags": {"buy": 0, "sell": 1}}}

    for s in SEEDS:
        se = events["seeds"][str(s)]
        for kind in ("buy", "sell"):
            evs = se["buys"] if kind == "buy" else se["sells"]
            block = out[f"control_{kind}"].setdefault(str(s), {})
            for h in HORIZONS:
                hs = str(h)
                n_ev = se[f"n_{kind}_h"][hs]
                if n_ev == 0:
                    block[hs] = {"n": 0}
                    continue
                rl_vals = np.asarray([ev["r"][hs] for ev in evs.values()
                                      if hs in ev["r"]])
                counts = {}
                for ev in evs.values():
                    if hs in ev["r"]:
                        counts[ev["regime"]] = counts.get(ev["regime"], 0) + 1
                rng = np.random.default_rng(regime_key(s, h, kind))
                cmean, cmed, rep0 = mc_control(closes, creg, counts, h, N_REP, rng)
                block[hs] = {"n": int(n_ev), "rl_mean": round(float(rl_vals.mean()), 8),
                             "rl_median": round(float(np.median(rl_vals)), 8),
                             "ctrl_mean_rep": [round(float(x), 8) for x in cmean],
                             "ctrl_median_rep": [round(float(x), 8) for x in cmed],
                             "ctrl_sample_rep0": [round(float(x), 8) for x in rep0]}

        # regime-conditional BUY summary @ h=12 (descriptive)
        rng = np.random.default_rng(regime_key(s, PRIMARY_H, "buy"))
        rc = {}
        for r in set(events["seeds"][str(s)]["regime_buy_counts"]):
            cnt = events["seeds"][str(s)]["regime_buy_counts"][r]
            if cnt <= 0:
                continue
            pool = draws_at(closes, creg, eligible_steps(creg, PRIMARY_H, r), PRIMARY_H)
            rl_r = [ev["r"][str(PRIMARY_H)] for ev in se["buys"].values()
                    if str(PRIMARY_H) in ev["r"] and ev["regime"] == r]
            means = np.asarray([pool[rng.integers(0, len(pool), size=cnt)].mean()
                                for _ in range(N_REP)])
            rl_m = float(np.mean(rl_r))
            rc[r] = {"n": len(rl_r), "rl_mean": round(rl_m, 6),
                     "rl_median": round(float(np.median(rl_r)), 6),
                     "ctrl_mean_med": round(float(np.median(means)), 6),
                     "ctrl_mean_lo": round(float(np.percentile(means, 2.5)), 6),
                     "ctrl_mean_hi": round(float(np.percentile(means, 97.5)), 6),
                     "mc_p": round(float((means >= rl_m).mean()), 4)}
        out["regime_buy"][str(s)] = rc

        out["freqai_buy"][str(s)] = freqai_events(s, closes, date2idx)

    json.dump(out, open(D47 / "forward418.json", "w", encoding="utf-8"), indent=2, default=str)

    print("== BUY & HOLD ==", out["buy_hold"])
    print("== Trend (mean fwd return over ALL random steps, per horizon) ==", out["drift_h"])
    for s in SEEDS:
        cell = out["control_buy"][str(s)][str(PRIMARY_H)]
        if cell.get("n", 0) == 0:
            print(f"  seed {s:>4} BUY h={PRIMARY_H}: n=0 (sinyal yok)")
            continue
        meds = np.median(cell["ctrl_median_rep"])
        print(f"  seed {s:>4} BUY h={PRIMARY_H}: n={cell['n']} rl_mean={cell['rl_mean']:.6f} "
              f"rl_median={cell['rl_median']:.6f} ctrl_mean_med="
              f"{np.median(cell['ctrl_mean_rep']):.6f} ctrl_med_med={meds:.6f} "
              f"| regimes={out['regime_buy'].get(str(s), {})}")
    for s in SEEDS:
        fa = out["freqai_buy"][str(s)]
        print(f"  seed {s:>4} FreqAI: status={fa['status']} entries={fa['n_entries']} "
              f"unmatched={fa['unmatched']} n_h12={fa['n_h'].get('12')} "
              f"mean12={fa['mean_h'].get('12')}")
    print("\nforward418.json yazildi:", D47 / "forward418.json")


if __name__ == "__main__":
    main()