"""Phase 4.7 aggregation — READ-ONLY (eğitim yok, tuning yok)."""
import glob
import json
import statistics

D = "experiments/phase_04_rl/tuning47"
runs = {}
for p in sorted(glob.glob(D + "/run_E*.json")):
    r = json.load(open(p, encoding="utf-8"))
    runs.setdefault(r["config"], {})[r["seed"]] = r

print("== per-config (mean/median/std val Sharpe) ==")
table = {}
for cid in sorted(runs):
    sh = [runs[cid][s]["val"]["daily_sharpe"] for s in [42, 7, 123, 2026, 999]]
    table[cid] = {"mean": statistics.mean(sh), "median": statistics.median(sh),
                  "std": statistics.stdev(sh) if len(set(sh)) > 1 else 0.0,
                  "sharpes": sh}
    print(" %s mean=%+.4f median=%+.4f std=%.4f %s" % (
        cid, table[cid]["mean"], table[cid]["median"], table[cid]["std"],
        ["%+.3f" % x for x in sh]))

order = sorted(table, key=lambda c: (-table[c]["mean"], -table[c]["median"],
                                     table[c]["std"], c))
print("sıralama:", order)
sel = order[0]
print("selected:", sel, "(kural: mean -> tie +-0.05 -> median -> std -> kucuk id)")

print("== selected config tum seedler ==")
for s in [42, 7, 123, 2026, 999]:
    r = runs[sel][s]
    v = r["val"]
    a = {int(k): vv for k, vv in r["val_actions"].items()}
    print(" seed %s: Sharpe=%s net=%s n=%s WR=%s PF=%s DD=%s acts=%s flips=%s "
          "hold_med=%s fee=%s slip=%s term=%s bank=%s gates=%s" % (
              s, v["daily_sharpe"], v["net_abs"], v["trade_count"], v["win_rate"],
              v["profit_factor"], v["max_dd"], a, r["val_flips"],
              r["val_med_hold_min"], r["val_fee_total"], r["val_slip_total"],
              r["val_term_reason"], r["val_bankruptcy"], r["gates"]))

print("== patoloji taraması (40 koşu) ==")
pats = {"zero_trade": 0, "only_hold": 0, "buy_no_sell": 0, "single_trade": 0,
        "bankruptcy": 0, "forced": 0, "fee_gt_gross": 0, "dd_gt_20": 0}
for cid in runs:
    for s in runs[cid]:
        r = runs[cid][s]
        a = {int(k): vv for k, vv in r["val_actions"].items()}
        if r["val"]["trade_count"] == 0:
            pats["zero_trade"] += 1
        if a.get(1, 0) == 0 and a.get(2, 0) == 0:
            pats["only_hold"] += 1
        if a.get(1, 0) > 0 and a.get(2, 0) == 0:
            pats["buy_no_sell"] += 1
        if r["val"]["trade_count"] == 1:
            pats["single_trade"] += 1
        if r["val_bankruptcy"]:
            pats["bankruptcy"] += 1
        if "forced" in r["val_term_reason"]:
            pats["forced"] += 1
        if r["val_fee_total"] > (r["val_gross_total"] if "val_gross_total" in r else 0):
            pats["fee_gt_gross"] += 1
        if abs(r["val"]["max_dd"]) > 0.20:
            pats["dd_gt_20"] += 1
print(pats)
from collections import Counter
hfails, warns = Counter(), Counter()
for cid in runs:
    for s in runs[cid]:
        g = runs[cid][s]["gates"]
        for h in g["hard_fails"]:
            hfails[h.split(":")[0] if ":" in h else h] += 1
        for w in g["warnings"]:
            warns[w] += 1
print("gate hard-fail ozeti:", dict(hfails))
print("gate warning ozeti:", dict(warns))
print("== E1 diagnostics ozeti (entropy/kl son rollout) ==")
for s in [42, 7, 123, 2026, 999]:
    try:
        rows = [json.loads(x) for x in
                open(D + f"/diag_E1_seed{s}.jsonl", encoding="utf-8").read().strip().split("\n")]
        last = rows[-1]
        ent = [r.get("log_train/entropy_loss", float("nan")) for r in rows]
        import math
        ent = [e for e in ent if isinstance(e, float) and math.isfinite(e)]
        print(" seed %s: rollout=%s mean_ent=%.4f last_kl=%s last_clip=%s" % (
            s, len(rows), sum(ent) / len(ent) if ent else float("nan"),
            last.get("log_train/approx_kl"), last.get("log_train/clip_fraction")))
    except FileNotFoundError:
        print(" seed %s: diag yok" % s)
out = {"selection": sel, "table": table, "order": order, "pathologies": pats,
       "gate_hard_fails": dict(hfails), "gate_warnings": dict(warns)}
json.dump(out, open(D + "/comparison.json", "w", encoding="utf-8"), indent=2)
print("yazıldı: comparison.json")
