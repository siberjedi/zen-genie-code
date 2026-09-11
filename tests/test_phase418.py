"""Phase 4.18 - Testler (plain-python runner).

Kapsam: event extraction, forward indexing, off-by-one, horizon truncation,
MC reproducibility, regime matching, stats fonksiyonlari, seed-cluster
bootstrap, decomposition, leakage guards.

Calistir: py -3 tests/test_phase418.py
"""
import json
import pathlib
import sys
import warnings

warnings.filterwarnings("ignore", module="scipy")

TESTROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(TESTROOT))

import numpy as np

from scripts.phase418_events import build_events, forward_returns, track_positions
from scripts.phase418_forward import (draws_at, drift_h, eligible_steps,
                                      mc_control, regime_key)
from scripts.phase418_stats import (benjamini_hochberg, cell_tests, cliff_delta,
                                    cluster_bootstrap_ci, cohens_d, power_of,
                                    welch_ci)
from scripts.phase418_decomp import decompose
from scripts.phase416_drift import load_val, simulate

D47 = TESTROOT / "experiments" / "phase_04_rl" / "tuning47"
PASSED = []


def check(name, cond):
    PASSED.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        raise AssertionError(name)


def toy_closes(n_actions=100, step=0.1):
    n = n_actions + 31
    return np.asarray([100.0 + i * step for i in range(n)], dtype=float)


def toy_creg(closes, bull_frac=0.7):
    regs = ["bull"] * int(len(closes) * bull_frac) + \
        ["bear"] * (len(closes) - int(len(closes) * bull_frac))
    return np.asarray(regs)


def real_sized():
    """Gercek boyuta uygun sentetik (module N_TRADABLE=51794, len=51825)."""
    closes = np.concatenate([np.linspace(100.0, 105.0, 30000),
                             np.full(51825 - 30000, 105.0)])
    creg = np.asarray(["bull"] * 30000 + ["bear"] * (51825 - 30000))
    return closes, creg


# ---------------------------------------------------------------- 1) event extraction
def test_event_extraction():
    ac = np.zeros(100, dtype=int)
    ac[0] = 1; ac[10] = 2; ac[20] = 1; ac[30] = 2
    ac[40] = 1; ac[50] = 2; ac[60] = 1; ac[70] = 2; ac[80] = 1; ac[90] = 2
    ac[5] = 1    # long iken action 1 -> no-op
    ac[95] = 2   # flat iken action 2 -> no-op
    closes = toy_closes()
    creg = toy_creg(closes)
    buys, sells, pre_pos, eq, trades = track_positions(ac, closes)
    check("event extraction: 5 gercek BUY (all-in no-op sayilmaz)", len(buys) == 5)
    check("event extraction: 5 gercek SELL", len(sells) == 5)
    check("event extraction: 5 trade tamamlandi", len(trades) == 5)
    check("event extraction: exposure 0.5 (50/100 steps long)", abs(sum(pre_pos) / 100 - 0.5) < 1e-9)
    ev = build_events(ac, closes, creg, [1, 3, 12])
    for k in buys:
        check(f"event extraction: BUY k={k} -> execution candle 30+k",
              ev["buys"][int(k)]["c"] == 30 + int(k))
        check(f"event extraction: BUY k={k} base==close[30+k]",
              abs(ev["buys"][int(k)]["base"] - closes[30 + int(k)]) < 1e-12)
    check("event extraction: n_events_buy==5", ev["n_events_buy"] == 5)
    check("event extraction: n_events_sell==5", ev["n_events_sell"] == 5)
    print("ok")


# ----------------------------------------------------------------- 2) forward indexing
def test_forward_indexing():
    closes = toy_closes()
    ev = forward_returns(closes, [0, 5], [1, 3])
    r1 = closes[30 + 0 + 1] / closes[30 + 0] - 1.0
    check("forward r_h=1 exact", abs(ev[0]["r"]["1"] - r1) < 1e-12)
    r3 = closes[30 + 0 + 3] / closes[30 + 0] - 1.0
    check("forward r_h=3 exact", abs(ev[0]["r"]["3"] - r3) < 1e-12)
    check("forward base == execution candle close",
          abs(ev[0]["base"] - closes[30 + 0]) < 1e-12)
    check("forward k key type int (JSON'a string olarak duser)", isinstance(ev[0]["k"], int))
    r1_k5 = closes[30 + 5 + 1] / closes[30 + 5] - 1.0
    check("forward r_h=1 k=5 exact", abs(ev[5]["r"]["1"] - r1_k5) < 1e-12)
    print("ok")


# ------------------------------------------------------------- 3) horizon truncation
def test_horizon_truncation():
    n = 10
    closes = toy_closes(n_actions=n)
    ev = forward_returns(closes, [0], [1, 3, 12])
    check("truncation: k=0 h=12 (c+h=42>40) drop", "12" not in ev[0]["r"])
    check("truncation: k=0 h=1,3 kept", "1" in ev[0]["r"] and "3" in ev[0]["r"])
    ev2 = forward_returns(closes, [8], [1, 3, 12])   # c=38, len-1=40
    check("truncation: k=8 h=3 (41>40) drop", "3" not in ev2[8]["r"])
    check("truncation: k=8 h=12 drop", "12" not in ev2[8]["r"])
    check("truncation: k=8 h=1 kept (39<=40)", "1" in ev2[8]["r"])
    print("ok")


# ---------------------------------------------------------------- 4) MC reproducibility
def test_mc_reproducibility():
    closes, creg = real_sized()
    counts = {"bull": 4, "bear": 2}
    key = regime_key(42, 12, "buy")
    m1, d1, s1 = mc_control(closes, creg, counts, 12, 200, np.random.default_rng(key))
    m2, d2, s2 = mc_control(closes, creg, counts, 12, 200, np.random.default_rng(key))
    check("MC reproducibility: ayni seed -> ozdes dizilim",
          np.array_equal(m1, m2) and np.array_equal(d1, d2))
    key3 = regime_key(43, 12, "buy")
    m3, _, _ = mc_control(closes, creg, counts, 12, 200, np.random.default_rng(key3))
    check("MC: farkli seed -> en az bir deger farkli", not np.array_equal(m1, m3))
    check("MC: rep0 sample boyutu == sum(counts)", len(s1) == sum(counts.values()))
    check("MC: buy/sell kind seed farki ayrışır",
          regime_key(42, 12, "buy") != regime_key(42, 12, "sell"))
    print("ok")


# ---------------------------------------------------------------- 5) regime matching
def test_regime_matching():
    closes, creg = real_sized()
    for r in ("bull", "bear"):
        ks = eligible_steps(creg, 12, r)
        check(f"regime matching: pool {r} bos degil", len(ks) > 0)
        ok = all(creg[30 + int(k)] == r and 30 + int(k) + 12 <= len(closes) - 1
                 for k in ks)
        check(f"regime matching: pool {r} yalniz kendi rejimi + h guard", ok)
    ks_all = eligible_steps(creg, 1, None)
    check("regime matching: None = tum eligible step'ler",
          np.all(draws_at(closes, creg, ks_all, 1) ==
                 np.array([closes[30 + int(k) + 1] / closes[30 + int(k)] - 1.0
                           for k in ks_all])))
    _, _, rep0_bull = mc_control(closes, creg, {"bull": 5}, 12, 100,
                                 np.random.default_rng(11))
    check("regime matching: bull havuzu (yukseken) ortalama > 0",
          rep0_bull.mean() > 0)
    _, _, rep0_bear = mc_control(closes, creg, {"bear": 5}, 12, 100,
                                 np.random.default_rng(12))
    check("regime matching: bear havuzu (sabit) ortalama ~ 0",
          abs(rep0_bear.mean()) < 1e-12)
    print("ok")


# ---------------------------------------------------------------------- 6) stats
def test_stats():
    x = np.asarray([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.asarray([0.1, 0.2, 0.3, 0.4, 0.5])
    cd = cliff_delta(x, y)
    check("cliff_delta x>y pozitif ve <=1", 0 < cd <= 1)
    md, lo, hi = welch_ci(x, y)
    check("welch CI mean farki kapsar", lo <= md <= hi)
    check("cohens_d pozitif", cohens_d(x, y) > 0)
    check("power_of n ile artar", power_of(0.5, 100, 100) > power_of(0.5, 10, 10))
    check("power_of buyuk d -> yuksek", power_of(1.0, 50, 50) > 0.8)
    q = benjamini_hochberg([0.01, 0.05, 0.1, 0.5])
    check("BH q monoton artan (p artan siralidaysa)", q == sorted(q))
    q2 = benjamini_hochberg([0.5, 0.1, 0.05, 0.01])
    check("BH q <= 1 ve en kucuk q == min(p)*m/m", max(q2) <= 1.0 and q2[3] == 0.01)
    small = cell_tests(np.asarray([0.1, -0.2, 0.3]), np.zeros(2000) + 0.01,
                       np.zeros(2000), np.asarray([0.01] * 5), "buy",
                       np.random.default_rng(1))
    check("stats: n<12 -> EVALUABLE DEGIL", small["flag"] == "EVALUABLE DEGIL")
    rng_c = np.random.default_rng(2)
    rl = rng_c.normal(0.0, 0.1, 25)
    ctrl0 = rng_c.normal(0.0, 0.1, 25)
    crit = cell_tests(rl, np.zeros(2000), np.zeros(2000), ctrl0, "buy",
                      np.random.default_rng(3))
    check("stats: d~0 -> LOW POWER", crit["flag"] == "LOW POWER")
    check("stats: n>=12 evaluable", crit["evaluable"])
    print("ok")


# ---------------------------------------------------- 7) seed-cluster bootstrap
def test_seed_cluster_bootstrap():
    diffs = {"42": 0.001, "7": -0.0005, "123": 0.0001, "999": -0.0002}
    m1, lo1, hi1 = cluster_bootstrap_ci(diffs, np.random.default_rng(7), iters=2000)
    m2, lo2, hi2 = cluster_bootstrap_ci(diffs, np.random.default_rng(7), iters=2000)
    check("cluster bootstrap reproducible", (m1 == m2 and lo1 == lo2 and hi1 == hi2))
    check("cluster bootstrap: lo<=hi", lo1 <= hi1)
    check("cluster bootstrap metric = seed ortalamasi",
          abs(m1 - np.mean(list(diffs.values()))) < 1e-12)
    m3, lo3, hi3 = cluster_bootstrap_ci({"a": 1.0, "b": 1.0, "c": 1.0},
                                        np.random.default_rng(8), iters=2000)
    check("cluster bootstrap: sabit seedlar -> sabit CI",
          lo3 == hi3 == m3)
    print("ok")


# ----------------------------------------------------------------- 8) decomposition
def test_decomposition():
    full, vdf = load_val()
    closes = vdf["close"].values.astype(float)
    art = json.load(open(D47 / "art_E1_seed42.json", encoding="utf-8"))
    actions = np.asarray(art["actions"], dtype=int)
    act_bh = ["B"] + [None] * (len(closes) - 1 - 30)
    tr_bh, _, _ = simulate(act_bh, closes)
    bh_g = float(closes[-1] / closes[30] - 1.0)
    bh_n = float(sum(t["profit"] for t in tr_bh) / 100.0)
    d = decompose(42, actions, closes, bh_g, bh_n)
    check("decomp: identity gross tam", d["identity_gross_ok"])
    check("decomp: identity net tam", d["identity_net_ok"])
    check("decomp: reentry anchor 4.16 (~0.6228)", abs(d["reentry_net"] - 0.6228) < 1e-3)
    check("decomp: timing_reentry 4.16 (~-0.2478)",
          abs(d["timing_reentry"] - (-0.2478)) < 1e-3)
    check("decomp: E 0.4046 (4.17)", abs(d["exposure_E"] - 0.4046) < 1e-3)
    print("ok")


# ------------------------------------------------------------ 9) leakage guards (real)
def test_leakage_guards_real():
    ev = json.load(open(D47 / "events418.json", encoding="utf-8"))
    check("leakage: audit PASSED", ev["meta"]["leakage_audit"]["passed"])
    check("leakage: replay equality all seeds",
          all(v["ok"] for v in ev["meta"]["leakage_audit"]["replay_equality"].values()))
    full, vdf = load_val()
    closes = vdf["close"].values.astype(float)
    per_seed = {"42": {"n": 0, "c_eq": 0, "base_eq": 0, "obs_safe": 0, "rh_exact": 0},
                "999": {"n": 0, "c_eq": 0, "base_eq": 0, "obs_safe": 0, "rh_exact": 0}}
    for s_ in per_seed:
        for evl in ev["seeds"][s_]["buys"].values():
            c = evl["c"]; k = evl["k"]
            rh_ok = all(abs(r - (closes[c + int(h)] / closes[c] - 1.0)) < 1e-9
                        for h, r in evl["r"].items())
            per_seed[s_]["n"] += 1
            per_seed[s_]["c_eq"] += (c == 30 + k)
            per_seed[s_]["base_eq"] += (abs(evl["base"] - closes[c]) < 1e-9)
            per_seed[s_]["obs_safe"] += ((k + 29) < c)
            per_seed[s_]["rh_exact"] += rh_ok
    for s_, m in per_seed.items():
        total = m["n"]
        check(f"leakage: seed {s_} {total} event; c==30+k, base==close[c], "
              f"obs<exec, r_h exact (hepsi)",
              total > 0 and all(m[k] == total for k in ("c_eq", "base_eq",
                                                        "obs_safe", "rh_exact")))
    check("leakage: seed42 buy n=40 (trade count)", ev["seeds"]["42"]["n_events_buy"] == 40)
    print("ok")


def main():
    tests = [test_event_extraction, test_forward_indexing, test_horizon_truncation,
             test_mc_reproducibility, test_regime_matching, test_stats,
             test_seed_cluster_bootstrap, test_decomposition, test_leakage_guards_real]
    for t in tests:
        print(f"== {t.__name__} ==")
        t()
    n_ok = sum(1 for _, ok in PASSED if ok)
    print(f"\nALL PASS - {n_ok}/{len(PASSED)} checks (training YOK)")
    if n_ok != len(PASSED):
        sys.exit(1)


if __name__ == "__main__":
    main()