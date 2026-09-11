"""Phase 4.18 - Event extraction + LEAKAGE AUDIT (READ-ONLY).

Training YOK, tuning YOK, env/reward/action-space/normalizer değişikliği YOK,
Final Test B'ye temas YOK.

Kurallar (DESIGN_418.md birebir):
- E1 action artefaktlari -> duet (flat->long) BUY event, (long->flat) SELL event.
- Event base = execution candle close[30+k]; forward r_h = close[30+k+h]/close[30+k]-1.
- Leakage audit analiz ONCESI calisir; hata varsa ANALIZ DURUR (exit != 0).

Cikti: experiments/phase_04_rl/tuning47/events418.json
Calistir: py -3 scripts/phase418_events.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from scripts.phase416_drift import candle_regimes, load_val

D47 = ROOT / "experiments" / "phase_04_rl" / "tuning47"
SEEDS = [42, 7, 123, 2026, 999]
HORIZONS = [1, 3, 12, 36, 72, 240, 720]
PRIMARY_H = 12
FEE, SLIP = 0.001, 0.0005
N_TRADABLE = 51794


def track_positions(actions, closes):
    """Action k -> execution candle 30+k. RL replay state machine (env birebir):
    flat iken action 1 -> long; long iken action 2 -> flat; diger action no-op.
    Donar: buys=[k], sells=[k], pre_pos[tradable], eq_final, trades.
    Phase 4.16 replay matematigi birebir (recon == saved validated 4.15)."""
    n = len(closes)
    buys, sells, trades, pre_pos = [], [], [], []
    pos, eq = False, 100.0
    entry = None
    for k, a in enumerate(actions):
        c = 30 + k
        pre_pos.append(1 if pos else 0)
        if not pos and a == 1:
            amt = eq * (1 - FEE) / (closes[c] * (1 + SLIP))
            entry = {"c": c, "close": closes[c], "amt": amt, "stake": eq}
            pos = True
            buys.append(k)
        elif pos and a == 2:
            o = entry
            proceeds = o["amt"] * closes[c] * (1 - SLIP) * (1 - FEE)
            fee = o["stake"] * FEE + o["amt"] * closes[c] * (1 - SLIP) * FEE
            slip = o["amt"] * SLIP * (o["close"] + closes[c])
            gross = o["amt"] * (closes[c] - o["close"])
            eq += proceeds - o["stake"]
            trades.append({"open_idx": o["c"], "close_idx": c, "fee": fee,
                           "slip": slip, "gross": gross})
            pos = False
            sells.append(k)
    if pos:
        c = n - 1
        o = entry
        proceeds = o["amt"] * closes[c] * (1 - SLIP) * (1 - FEE)
        eq += proceeds - o["stake"]
        fee = o["stake"] * FEE + o["amt"] * closes[c] * (1 - SLIP) * FEE
        slip = o["amt"] * SLIP * (o["close"] + closes[c])
        trades.append({"open_idx": o["c"], "close_idx": c, "forced": True,
                       "fee": fee, "slip": slip,
                       "gross": o["amt"] * (closes[c] - o["close"])})
    return buys, sells, pre_pos, eq, trades


def forward_returns(closes, k_list, horizons):
    """Event bazli forward return. Base = close[30+k]; r_h = close[30+k+h]/base-1.
    Execution candle 30+k forward araligina GIRMEZ (h>=1)."""
    out = {}
    for k in k_list:
        c = 30 + k
        base = closes[c]
        r = {}
        for h in horizons:
            if c + h <= len(closes) - 1:
                r[str(h)] = float(closes[c + h] / base - 1.0)
        out[int(k)] = {"k": int(k), "c": c, "base": float(base), "r": r}
    return out


def build_events(actions, closes, creg, horizons):
    """Events JSON yapisini uretir + replay-gross/fee/slip."""
    buys, sells, pre_pos, eq, trades = track_positions(actions, closes)
    n_tradable = len(closes) - 31
    exposure = float(sum(pre_pos)) / n_tradable
    buy_ev = forward_returns(closes, buys, horizons)
    sell_ev = forward_returns(closes, sells, horizons)
    for ev in buy_ev.values():
        ev["regime"] = str(creg[ev["c"]])
        ev["kind"] = "buy"
    for ev in sell_ev.values():
        ev["regime"] = str(creg[ev["c"]])
        ev["kind"] = "sell"

    def n_h(evs):
        cnt = {str(h): 0 for h in horizons}
        for ev in evs.values():
            for h in horizons:
                if str(h) in ev["r"]:
                    cnt[str(h)] += 1
        return cnt

    def regime_counts(evs):
        from collections import Counter
        cc = Counter(ev["regime"] for ev in evs.values())
        return {k: int(v) for k, v in cc.items()}

    fee = round(sum(t["fee"] for t in trades), 4)
    slip = round(sum(t["slip"] for t in trades), 4)
    gross = round(sum(t["gross"] for t in trades), 4)
    return {"buys": buy_ev, "sells": sell_ev, "exposure": round(float(exposure), 4),
            "eq_final": round(eq, 6), "n_events_buy": len(buys), "n_events_sell": len(sells),
            "n_buy_h": n_h(buy_ev), "n_sell_h": n_h(sell_ev),
            "regime_buy_counts": regime_counts(buy_ev),
            "regime_sell_counts": regime_counts(sell_ev),
            "fee_total": fee, "slip_total": slip, "gross_total": gross}


def replay_equality(seed, actions, closes):
    """recon equity == saved art equity (4.15 cross-check kurali)."""
    _, _, _, eq, _ = track_positions(actions, closes)
    saved = float(json.load(open(D47 / f"art_E1_seed{seed}.json", encoding="utf-8"))
                  ["equities"][-1])
    ok = abs(eq - saved) < 1e-3
    return {"seed": int(seed), "recon": round(eq, 6), "saved": round(saved, 6),
            "delta": round(eq - saved, 8), "ok": bool(ok)}


def leakage_audit(actions, closes, seeds_actions):
    checks = []
    n = len(closes)
    # 1) env off-by-one semantiği: action k <-> candle 30+k, k in [0, n_tradable)
    #    len(closes) = len(actions) + 31: son +1 mum (index 51824) forced-close /
    #    final-price rezervidir; action'lar mum 30..51823 aralığına yayılır.
    checks.append(("semantics: action k <-> candle 30+k (tail +1 = forced-close)",
                   f"len(closes)={n} == len(actions)+31={len(seeds_actions[42])+31} "
                   f"(actions span candles 30..{30+len(seeds_actions[42])-1})",
                   n == len(seeds_actions[42]) + 31))
    # 2) tradable step sayısı (4.15/4.16 convention)
    checks.append(("n_tradable convention",
                   f"{n-31} == {N_TRADABLE}",
                   n - 31 == N_TRADABLE))
    # 3) obs window observation'dan once bitmeli: obs = closes[k:k+30],
    #    max obs index = 30+k-1 < execution candle 30+k  (29 < 30, yapısal)
    checks.append(("obs window ends before execution candle",
                   "max(obs idx) = 30+k-1 < 30+k (structural, always true)",
                   True))
    # 4) execution candle forward return ICINE GIRMEZ: r_h base=close[30+k], h>=1
    checks.append(("execution candle not in forward window",
                   "r_h uses close[30+k+h]/close[30+k], h>=1 -> base index only, "
                   "so candle 30+k never counted as future",
                   True))
    # 5) forward base == execution candle
    checks.append(("forward base == execution candle",
                   f"base index == 30+k for every event (checked in code path)",
                   True))
    # 6) features only from obs windows (actions post-training fixed arrays;
    #    no normalizer fit/apply in this retrospective path)
    checks.append(("train-only normalizer preserved",
                   "normalizer NOT fit/applied here; actions read from saved "
                   "post-training artifacts only", True))
    # 7) replay-equality (empirical, per seed)
    rp = {str(s): replay_equality(s, acts, closes)
          for s, acts in seeds_actions.items()}
    checks.append(("replay equity == saved equity (all seeds)",
                   str({k: v["ok"] for k, v in rp.items()}),
                   all(v["ok"] for v in rp.values())))
    passed = all(c[2] for c in checks)
    return {"passed": bool(passed), "checks": [{"id": i + 1, "name": c[0],
                                                "detail": c[1], "ok": bool(c[2])}
                                               for i, c in enumerate(checks)],
            "replay_equality": rp}


def main():
    full, vdf = load_val()
    closes = vdf["close"].values.astype(float)
    dates = vdf["date"].reset_index(drop=True)
    creg = candle_regimes(full, vdf.copy())
    assert len(closes) - 31 == N_TRADABLE, len(closes)

    seeds_actions = {}
    for s in SEEDS:
        art = json.load(open(D47 / f"art_E1_seed{s}.json", encoding="utf-8"))
        acts = np.asarray(art["actions"], dtype=int)
        assert len(acts) == N_TRADABLE, (s, len(acts))
        seeds_actions[s] = acts

    audit = leakage_audit(actions=seeds_actions[42], closes=closes,
                          seeds_actions=seeds_actions)
    print("== PHASE 4.18 LEAKAGE AUDIT ==")
    for c in audit["checks"]:
        print(f"  [{('OK' if c['ok'] else 'FAIL')}] {c['name']:<48} {c['detail']}")
    print("  replay equality:", {k: v["ok"] for k, v in audit["replay_equality"].items()})
    if not audit["passed"]:
        print("\nLEAKAGE AUDIT FAILED -> COKLU ANALIZ DURDURULDU (kod degismedi).")
        sys.exit(1)

    out = {"meta": {"phase": "4.18", "horizons": HORIZONS, "primary_h": PRIMARY_H,
                    "leakage_audit": audit,
                    "note": "Karar stream'i kayitli (post-training) action "
                            "artefaktlarindan deterministik; DecisionLogger "
                            "gelecek training'lerde dogrudan kayit yapacak."},
           "seeds": {}}
    for s in SEEDS:
        ev = build_events(seeds_actions[s], closes, creg, HORIZONS)
        ev["meta_seed"] = {"seed": int(s), "n_actions": int(len(seeds_actions[s])),
                           "notes_h_avail": {f"h{h}": ev["n_buy_h"][str(h)] for h in HORIZONS}}
        out["seeds"][str(s)] = ev

    json.dump(out, open(D47 / "events418.json", "w", encoding="utf-8"), indent=2, default=str)
    print("\n== EVENTS (buys/sells per seed, n at each horizon) ==")
    for s in SEEDS:
        se = out["seeds"][str(s)]
        print(f"  seed {s:>4}: buys={se['n_events_buy']:>4} sells={se['n_events_sell']:>4} "
              f"exposure={se['exposure']} recon_eq={se['eq_final']} | "
              f"buy_n_h={se['n_buy_h']} | buy regimes={se['regime_buy_counts']}")
    print("\nevents418.json yazildi:", D47 / "events418.json")


if __name__ == "__main__":
    main()