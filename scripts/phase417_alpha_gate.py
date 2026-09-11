"""Phase 4.17 — Alpha Gate (LOCKED-DIAGNOSTIC; selection criterion DEĞİL).

G1–G5 tasarım onaylı olduğu haliyle uygulanır. Locked kriterlere DOKUNMAZ:
Sharpe >= 0.80, backtest/live gap < 0.35, 30 days.

Phase 4.16 engine'ini yeniden kullanır (scripts.phase416_drift modül yardımcıları).
Retrospektif olarak E1 5 seed'de çalışır; konsistens checksum'ları raporlar.

Standart girdiler: tuning47/art_E1_seed*.json + BTC_USDT-5m.feather
Çıktı: tuning47/gate417.json
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from scripts.phase416_drift import (load_val, candle_regimes, simulate,
                                    to_metric_trades, summarize, conc)
from src.backtest.evaluate import compute_power

D47 = ROOT / "experiments" / "phase_04_rl" / "tuning47"
SEEDS = [42, 7, 123, 2026, 999]
POWER_TARGET = 0.80     # locked power_target (phase_05)
ALPHA = 0.05
BE = 1e-9
# Benchmark set (gate'te): yalnızca B&H ve BULL. Re-entry attribution-only.
BENCH_LABELS = ["buy_hold", "bull_exposure"]


def daily_ratio_series(trades, dates):
    """Günlük net-return serisi — metrics_from_trades agregasyon convention'ı.

    trade close_idx -> close_date; o güne profit_ratio toplanır; boş günler 0.
    Index G1 için TAM pencereyi kapsar (2023-01-01..2023-06-30, 181 gün);
    locked metrics_from_trades 180 gün (06-29 son) kullanır — terminal günün
    P&L'si G1'de düşmesin diye bilinçli genişletme (diğer metrikler değişmedi).
    """
    idx = pd.date_range("2023-01-01", "2023-06-30", freq="D").date
    s = pd.Series(0.0, index=idx)
    for t in trades:
        d = dates.iloc[t["close_idx"]].date()
        s[d] = float(s[d]) + t["profit"] / t["stake"]
    return s


def rl_trades(acts, closes):
    """E1 seed replay — env birebir (fee/slip/execution), phase416 D ile aynı."""
    trades, pre_pos, eq = [], [], 100.0
    entry = None
    for k, a in enumerate(acts):
        c = 30 + k
        pre_pos.append(1 if entry is not None else 0)
        if entry is None and a == 1:
            amt = eq * (1 - 0.001) / (closes[c] * (1 + 0.0005))
            entry = {"c": c, "close": closes[c], "amt": amt, "stake": eq}
        elif entry is not None and a == 2:
            o = entry
            proceeds = o["amt"] * closes[c] * (1 - 0.0005) * (1 - 0.001)
            fee = o["stake"] * 0.001 + o["amt"] * closes[c] * (1 - 0.0005) * 0.001
            slip = o["amt"] * 0.0005 * (o["close"] + closes[c])
            gross = o["amt"] * (closes[c] - o["close"])
            trades.append({"open_idx": o["c"], "close_idx": c, "forced": False,
                           "open": o["close"], "close": closes[c], "stake": o["stake"],
                           "profit": proceeds - o["stake"], "fee": fee,
                           "slip": slip, "gross": gross})
            eq += proceeds - o["stake"]
            entry = None
    if entry is not None:
        c = len(closes) - 1
        o = entry
        proceeds = o["amt"] * closes[c] * (1 - 0.0005) * (1 - 0.001)
        fee = o["stake"] * 0.001 + o["amt"] * closes[c] * (1 - 0.0005) * 0.001
        slip = o["amt"] * 0.0005 * (o["close"] + closes[c])
        trades.append({"open_idx": o["c"], "close_idx": c, "forced": True,
                       "open": o["close"], "close": closes[c], "stake": o["stake"],
                       "profit": proceeds - o["stake"], "fee": fee, "slip": slip,
                       "gross": o["amt"] * (closes[c] - o["close"])})
        eq += proceeds - o["stake"]
    return trades, pre_pos, eq


def main():
    full, vdf = load_val()
    closes = vdf["close"].values.astype(float)
    dates = pd.to_datetime(vdf["date"]).reset_index(drop=True)
    creg = candle_regimes(full, vdf.copy())
    n_tradable = len(closes) - 31
    assert n_tradable == 51794, n_tradable

    # ---- lockable benchmark frame (B&H + Bull) ----
    bh_acts = ["B"] + [None] * (n_tradable - 1)
    tr_bh, pre_bh, _ = simulate(bh_acts, closes)
    bh = summarize("buy_hold", tr_bh, dates, closes, pre_bh)

    bull_actions, pos = [], False
    for c in range(30, len(closes) - 1):
        want = creg[c] == "bull"
        if not pos and want:
            bull_actions.append("B"); pos = True
        elif pos and not want:
            bull_actions.append("S"); pos = False
        else:
            bull_actions.append(None)
    tr_bull, pre_bull, _ = simulate(bull_actions, closes)
    bull = summarize("bull_exposure", tr_bull, dates, closes, pre_bull)

    # Locked Sharpe: run artifact'ında kayıtlı val.daily_sharpe (RESULT_47
    # convention'ı — trade-close-date agregasyonundan seed bazlı hafif farklı;
    # A-gate'i LOCKED değerlerle çalışır, G1-G4 bundan etkilenmez).
    locked_sharpe = {}
    for s in SEEDS:
        run = json.load(open(D47 / f"run_E1_seed{s}.json", encoding="utf-8"))
        locked_sharpe[s] = float(run["val"]["daily_sharpe"])

    benches = {"buy_hold": {"E": sum(pre_bh) / n_tradable,
                            "net": bh["net_abs"] / 100.0, "gross": bh["gross"] / 100.0,
                            "daily": daily_ratio_series(tr_bh, dates), "trades": tr_bh},
               "bull_exposure": {"E": sum(pre_bull) / n_tradable,
                                 "net": bull["net_abs"] / 100.0, "gross": bull["gross"] / 100.0,
                                 "daily": daily_ratio_series(tr_bull, dates), "trades": tr_bull}}
    R_BH_net = benches["buy_hold"]["net"]
    R_BH_gross = benches["buy_hold"]["gross"]

    out = {"meta": {"phase": "4.17", "mode": "LOCKED-DIAGNOSTIC",
                    "locked_criteria_untouched": ["sharpe>=0.80", "gap<0.35", "30 days"],
                    "power_target": POWER_TARGET, "alpha": ALPHA,
                    "benchmark_set": BENCH_LABELS,
                    "note": "Immediate Re-entry gate setinde YOK (attribution-only).",
                    "g3_note": "G3 aproximatif (exposure x B&H_net; compounding nedeniyle "
                               "descriptive, exact değil).",
                    "g1_note": "effect = mean(D)/std(D), n = günlük seri uzunluğu; "
                               "compute_power (TTestIndPower) kullanılır.",
                    "benchmarks": {k: {"E": v["E"], "net": round(v["net"], 4),
                                       "gross": round(v["gross"], 4)}
                                   for k, v in benches.items()}},
               "seeds": {}}

    seed_rows = []
    for seed in SEEDS:
        art = json.load(open(D47 / f"art_E1_seed{seed}.json", encoding="utf-8"))
        acts = np.asarray(art["actions"])
        trades, pre_pos, eq = rl_trades(acts, closes)
        met = summarize(f"rl_{seed}", trades, dates, closes, pre_pos)
        E = sum(pre_pos) / n_tradable
        net = met["net_abs"] / 100.0
        gross = met["gross"] / 100.0
        rl_daily = daily_ratio_series(trades, dates)

        # ---- G1: en yakın exposure benchmark еşleşme ----
        closest = min(BENCH_LABELS, key=lambda b: abs(benches[b]["E"] - E))
        D = rl_daily - benches[closest]["daily"]
        meanD = float(D.mean())
        sdD = float(D.std(ddof=1))
        n_days = int(len(D))
        if sdD == 0:
            power = float("nan")
        else:
            power = compute_power(meanD / sdD, n_days, ALPHA)
        if meanD <= 0:
            g1, g1_reason = "FAIL", f"mean(D)={meanD:+.4f} <= 0"
        elif np.isnan(power):
            g1, g1_reason = "NOT_EVALUABLE", "power=nan (statsmodels yok)"
        elif power >= POWER_TARGET:
            g1, g1_reason = "PASS", f"mean(D)={meanD:+.4f} power={power:.3f}>=0.80"
        else:
            g1, g1_reason = "NOT_EVALUABLE", f"power={power:.3f}<0.80 (yetersiz sample)"

        # ---- G2: timing alpha (gross) ----
        timing = gross - E * R_BH_gross
        g2 = "PASS" if timing > 0 else "FAIL"

        # ---- G3: net exposure eşleneği (approksimatif) ----
        ref_net = E * R_BH_net
        g3 = "PASS" if net >= ref_net - BE else "FAIL"

        # ---- G4: dominance (B&H + Bull) ----
        dominated = []
        for b in BENCH_LABELS:
            if benches[b]["E"] <= E + BE and benches[b]["net"] >= net - BE and \
               not (abs(benches[b]["E"] - E) < BE and abs(benches[b]["net"] - net) < BE):
                dominated.append(b)
        g4 = "PASS" if not dominated else f"FAIL ({','.join(dominated)})"

        # ---- G5: concentration (warn-only) ----
        net_real = float(sum(t["profit"] for t in trades)) if trades else 0.0
        c = conc(trades, net_real)
        g5 = (c.get("top3") or 0.0) >= 1.0

        # ---- overall (diagnostic) ----
        gates = {"G1": g1.split(" ")[0], "G2": g2, "G3": g3, "G4": g4.split(" ")[0]}
        gateB = all(gates[k] == "PASS" for k in gates)
        seed_rows.append(locked_sharpe[seed])
        overall = ("CANDIDATE-EDGE (A mean)", ("WEAK" if g5 else "STRONG"))
        if not gateB:
            overall = "NOT CANDIDATE (gate B fail)"

        seed_out = {
            "locked_sharpe_run": locked_sharpe[seed],
            "exposure": E, "net": net, "gross": gross,
            "n_trades": len(trades), "recon_final": round(eq, 3),
            "G1": {"status": g1, "reason": g1_reason, "bench": closest,
                   "meanD": round(meanD, 6), "power": round(power, 4) if not np.isnan(power) else None,
                   "n_days": n_days},
            "G2": {"status": g2, "timing_gross": round(timing, 6)},
            "G3": {"status": g3, "net": round(net, 6),
                   "E_x_BH_net_ref": round(ref_net, 6),
                   "note": "approksimatif (compounding)"},
            "G4": {"status": g4, "dominated_by": dominated},
            "G5": {"concentration_warning": g5, "top3_over_net": c.get("top3"),
                   "note": "DIAGNOSTIC only; selection gate değil"},
            "gateB": gateB,
            "overall": overall if isinstance(overall, str) else overall[0] + " / " + overall[1],
        }
        out["seeds"][str(seed)] = seed_out
        print(f"[seed {seed}] E={E:.4f} net={net*100:+.2f}% gross={gross*100:+.2f}% "
              f"Sh={met['sharpe']} | G1={g1} G2={g2} G3={g3} G4={g4} "
              f"G5warn={g5} | gateB={gateB} | {out['seeds'][str(seed)]['overall']}")

    out["ensemble"] = {"mean_locked_sharpe": round(float(np.mean(seed_rows)), 4),
                       "locked_sharpe_criterion": "mean >= 0.80",
                       "mean_sharpe_pass": float(np.mean(seed_rows)) >= 0.80}
    json.dump(out, open(D47 / "gate417.json", "w", encoding="utf-8"), indent=2, default=str)


if __name__ == "__main__":
    main()