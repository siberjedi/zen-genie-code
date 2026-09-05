"""Phase 4 aggregation — READ-ONLY (eğitim yok, tuning yok)."""
import glob
import json
import statistics

runs = {}
for p in sorted(glob.glob("experiments/phase_04_rl/results/run_*.json")):
    r = json.load(open(p, encoding="utf-8"))
    runs.setdefault(r["config"], {})[r["seed"]] = r

print("== hyperparams ==")
for cid in ["C0", "C1", "C2", "C3"]:
    print(" ", cid, runs[cid][42]["hyperparams"])

print("== per-run ==")
for cid in ["C0", "C1", "C2", "C3"]:
    for s in [42, 7, 123, 2026, 999]:
        r = runs[cid][s]
        v = r["val"]
        print(" %s/%s tr_rew=%s tr_eq=%s | Sharpe=%s net=%s n=%s WR=%s PF=%s DD=%s "
              "term=%s acts=%s flips=%s hold_med=%s fee=%s bank=%s" % (
                  cid, s, r["train_ep_reward"], r["train_final_equity"],
                  v["daily_sharpe"], v["net_abs"], v["trade_count"], v["win_rate"],
                  v["profit_factor"], v["max_dd"], r["val_term_reason"],
                  r["val_actions"], r["val_flips"], r["val_med_hold_min"],
                  r["val_fee_total"], r["val_bankruptcy"]))

print("== config stability (mean/median/std of val Sharpe) ==")
for cid in ["C0", "C1", "C2", "C3"]:
    sh = [runs[cid][s]["val"]["daily_sharpe"] for s in [42, 7, 123, 2026, 999]]
    sd = statistics.stdev(sh) if len(set(sh)) > 1 else 0.0
    print(" %s mean=%.4f median=%.4f std=%.4f" % (
        cid, statistics.mean(sh), statistics.median(sh), sd))
