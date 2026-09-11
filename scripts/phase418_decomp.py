"""Phase 4.18 - Exposure vs Timing decomposition (DESCRIPTIVE).

RL_net ~= DRIFT(E x R_BH) + TIMING - FRICTION
- DRIFT      = E x R_BH          (exposure-only expected return)
- FRICTION   = fee + slip        (% start)
- TIMING_net = RL_net - DRIFT_net + FRICTION
- TIMING_reentry = RL_net - REENTRY_net   (4.16 anchor: exposure-koruyucu pasif
                                            referans; RL valid SELL + hemen re-entry)

Camzalar: multi-trade compounding nedeniyle TUM dekompozisyon
DESCRIPTIVE / APPROXIMATE - kesin P&L ayristirmasi degildir.

Cikti: tuning47/decomp418.json
Calistir: py -3 scripts/phase418_decomp.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from scripts.phase416_drift import load_val, simulate
from scripts.phase418_events import track_positions

D47 = ROOT / "experiments" / "phase_04_rl" / "tuning47"
SEEDS = [42, 7, 123, 2026, 999]


def reentry_act_final(actions):
    """Phase 4.16 RE-ENTRY yardimcisi (birebir kopya)."""
    act_final, rl_was_long, we_long, pending = [], False, False, False
    for a in actions:
        rl_enter = (not rl_was_long) and a == 1
        rl_exit = rl_was_long and a == 2
        if rl_enter:
            rl_was_long = True
        if rl_exit:
            rl_was_long = False
        if not we_long and rl_enter:
            act_final.append("B"); we_long = True
        elif we_long and rl_exit:
            act_final.append("S"); we_long = False; pending = True
        elif pending:
            act_final.append("B"); we_long = True; pending = False
        else:
            act_final.append(None)
    return act_final


def decompose(seed, actions, closes, bh_gross, bh_net):
    buys, sells, pre_pos, eq_final, trades = track_positions(actions, closes)
    n_tradable = len(closes) - 31
    E = sum(pre_pos) / n_tradable
    rl_net = (eq_final - 100.0) / 100.0
    rl_gross = sum(t["gross"] for t in trades) / 100.0
    friction = (sum(t["fee"] for t in trades) + sum(t["slip"] for t in trades)) / 100.0

    drift_gross = E * bh_gross
    timing_gross = rl_gross - drift_gross
    drift_net = E * bh_net
    timing_net = rl_net - drift_net + friction

    act_re = reentry_act_final([int(a) for a in actions])
    tr_re, pre_re, eq_re = simulate(act_re, closes)
    reentry_net = sum(t["profit"] for t in tr_re) / 100.0
    reentry_exposure = sum(pre_re) / n_tradable
    timing_reentry = rl_net - reentry_net

    # identity checks (construction geregi tam)
    id_gross = abs(rl_gross - (drift_gross + timing_gross)) < 1e-12
    id_net = abs(rl_net - (drift_net + timing_net - friction)) < 1e-12
    assert id_gross and id_net

    return {"seed": int(seed), "rl_net_pct": round(rl_net, 6),
            "rl_gross_pct": round(rl_gross, 6),
            "exposure_E": round(float(E), 4),
            "bh_gross_pct": bh_gross, "bh_net_pct": bh_net,
            "drift_exposure_only_gross": round(float(drift_gross), 6),
            "drift_exposure_only_net": round(float(drift_net), 6),
            "timing_gross": round(float(timing_gross), 6),
            "timing_net": round(float(timing_net), 6),
            "friction_pct": round(float(friction), 6),
            "reentry_net": round(float(reentry_net), 6),
            "reentry_exposure": round(float(reentry_exposure), 4),
            "timing_reentry": round(float(timing_reentry), 6),
            "n_trades": len(trades),
            "identity_gross_ok": bool(id_gross), "identity_net_ok": bool(id_net),
            "note": "DESCRIPTIVE/APPROXIMATE (multi-trade compounding; "
                    "kesin P&L ayristirmasi degil)"}


def main():
    full, vdf = load_val()
    closes = vdf["close"].values.astype(float)
    actions_by_seed = {}
    for s in SEEDS:
        art = json.load(open(D47 / f"art_E1_seed{s}.json", encoding="utf-8"))
        actions_by_seed[s] = np.asarray(art["actions"], dtype=int)

    act_bh = ["B"] + [None] * (len(closes) - 1 - 30)
    tr_bh, _, eq_bh = simulate(act_bh, closes)
    bh_gross = float(closes[-1] / closes[30] - 1.0)
    bh_net = float(sum(t["profit"] for t in tr_bh) / 100.0)

    out = {"market": {"bh_gross_pct": round(bh_gross, 6),
                      "bh_net_pct": round(bh_net, 6),
                      "note": "DRIFT = exposure x R_BH; TIMING net residü = "
                              "RL_net - DRIFT_net + FRICTION (compounding dartigi)."},
           "seeds": {}}
    for s in SEEDS:
        out["seeds"][str(s)] = decompose(s, actions_by_seed[s], closes,
                                         bh_gross, bh_net)

    json.dump(out, open(D47 / "decomp418.json", "w", encoding="utf-8"), indent=2, default=str)

    print(f"Market: B&H gross={bh_gross*100:.3f}% net={bh_net*100:.3f}%")
    print(f"{'seed':>5} {'E':>7} {'RL_net':>9} {'DRIFT_g':>9} {'TIM_g':>9} "
          f"{'FRIC':>7} {'TIM_net':>9} {'REENTRY':>9} {'TIM_rentry':>9}")
    for s in SEEDS:
        d = out["seeds"][str(s)]
        print(f"{s:>5} {d['exposure_E']:>7.4f} {d['rl_net_pct']*100:>8.3f}% "
              f"{d['drift_exposure_only_gross']*100:>8.3f}% {d['timing_gross']*100:>8.3f}% "
              f"{d['friction_pct']*100:>6.3f}% {d['timing_net']*100:>8.3f}% "
              f"{d['reentry_net']*100:>8.3f}% {d['timing_reentry']*100:>8.3f}%")
    print("\ndecomp418.json yazildi:", D47 / "decomp418.json")


if __name__ == "__main__":
    main()