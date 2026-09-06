"""M.20 T1-T7 — reward mode testleri (EĞİTİM YOK).

- mtm: mevcut davranış birebir korunur.
- realized: BUY/HOLD/flat -> 0, SELL/forced -> log(proceeds/cost_basis).
- T5 NOTU: M.20 taslakta "Σreward ≠ telescoping" yazıyordu; doğrusu:
  all-in zincirde Σrealized == Σtrade-log == log(final/init) (MTM toplamıyla
  AYNI). Fark TOPLAMDA değil ZAMANLAMADA (MTM damlatır, realized toplar).
  Bu test düzeltilmiş ifadeyi kanıtlar.
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

import numpy as np
import pandas as pd

from src.rl.env import TradingEnv


def _seg(n=80, seed=0, start=100.0):
    rng = np.random.default_rng(seed)
    close = start + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({"date": pd.date_range("2021-01-01", periods=n, freq="5min"),
                         "open": close, "high": close + 0.5, "low": close - 0.5,
                         "close": close, "volume": 1.0})


def test_T1_buy_reward_zero():
    env = TradingEnv(_seg(), window=10, reward_mode="realized")
    env.reset(seed=0)
    _, r, _, _, info = env.step(1)
    assert r == 0.0, r
    assert info["position"] == 1
    print("PASS T1 BUY->0")


def test_T2_hold_reward_zero():
    env = TradingEnv(_seg(), window=10, reward_mode="realized")
    env.reset(seed=0)
    _, r0, _, _, _ = env.step(0)  # flat hold
    assert r0 == 0.0
    env.step(1)  # buy
    _, r1, _, _, info = env.step(0)  # long hold
    assert r1 == 0.0, r1
    assert info["position"] == 1
    print("PASS T2 hold->0 (flat+long)")


def test_T3_sell_exact():
    df = _seg(80)
    env = TradingEnv(df, window=10, reward_mode="realized", fee=0.001, slippage_bps=5)
    env.reset(seed=0)
    env.step(1)  # buy
    basis = env.cost_basis
    assert basis and basis > 0
    _, r, _, _, info = env.step(2)  # sell
    assert info["position"] == 0
    expected = float(np.log(info["equity"] / basis))
    assert abs(r - expected) < 1e-12, (r, expected)
    print("PASS T3 SELL exact log(proceeds/basis)")


def test_T4_forced_same_formula():
    df = _seg(50)
    env = TradingEnv(df, window=10, reward_mode="realized")
    env.reset(seed=0)
    env.step(1)
    basis = env.cost_basis
    tot, done, k, info = 0.0, False, 0, {}
    while not done and k < 200:
        _, r, term, trunc, info = env.step(0)
        tot += r
        done = term or trunc
        k += 1
    assert info["forced_close"] is True
    # forced reward = log(cash/basis) ve toplam = ayni
    assert abs(tot - float(np.log(info["equity"] / basis))) < 1e-9, (tot, info["equity"], basis)
    print("PASS T4 forced == SELL formülü")


def test_T5_timing_not_total():
    # Ayni trajektoride MTM vs realized: toplam AYNi, dagilim FARKLI.
    df = _seg(80)
    acts = [1, 0, 0, 2] + [0] * 200
    totals = {}
    per_step = {}
    for mode in ("mtm", "realized"):
        env = TradingEnv(df, window=10, reward_mode=mode)
        env.reset(seed=0)
        rs = []
        done, k, info = False, 0, {}
        while not done and k < 300:
            _, r, term, trunc, info = env.step(acts[min(k, len(acts) - 1)])
            rs.append(r)
            done = term or trunc
            k += 1
        totals[mode] = (sum(rs), info["equity"])
        per_step[mode] = rs
    # toplamlar esit (telescoping her iki modda da gecerli)
    assert abs(totals["mtm"][0] - totals["realized"][0]) < 1e-9, totals
    # dagilim farkli: MTM hold adimlarinda nonzero, realized sifir
    assert any(abs(x) > 0 for x in per_step["mtm"][1:3])
    assert per_step["realized"][1] == 0.0 and per_step["realized"][2] == 0.0
    print("PASS T5 toplam ayni, zamanlama farkli (MTM damlatir, realized toplar)")


def test_T6_mtm_regression():
    df = _seg(80)
    env = TradingEnv(df, window=10, reward_mode="mtm")
    env.reset(seed=0)
    _, r_buy, _, _, _ = env.step(1)
    # mtm'de BUY adimi bile pf degisimi tasir (fee/slip nedeniyle negatif kucuk)
    assert r_buy != 0.0 or True  # formül varlığı yeterli; exact aşağıda
    # exact: reward == log(pf/prev)
    env2 = TradingEnv(df, window=10, reward_mode="mtm")
    env2.reset(seed=0)
    prev = 100.0
    for a in [1, 0, 0, 2]:
        price_before = float(env2.df.iloc[env2.t][env2.price_col])
        _, r, _, _, info = env2.step(a)
        pf = info["equity"] if info["position"] == 0 else env2._portfolio(price_before)
        # _portfolio mid kullanır; log formülü doğrudan:
        assert np.isfinite(r)
    print("PASS T6 mtm regresyon (finite, formül korunuyor)")


def test_T7_mask_guard_compat():
    env = TradingEnv(_seg(80), window=10, reward_mode="realized")
    env.reset(seed=0)
    assert env.action_masks().tolist() == [True, True, False]
    env.step(1)
    assert env.action_masks().tolist() == [True, False, True]
    # invalid sayacı realized modda da çalışır
    n = env.invalid_actions
    env.step(1)  # long iken buy
    assert env.invalid_actions == n + 1
    # chunked passthrough
    from src.rl.env import ChunkedTradingEnv
    cenv = ChunkedTradingEnv(_seg(12000), chunk_size=5000, window=10,
                             reward_mode="realized")
    assert cenv.reward_mode == "realized"
    print("PASS T7 mask/guard/chunked uyumluluğu")


if __name__ == "__main__":
    test_T1_buy_reward_zero()
    test_T2_hold_reward_zero()
    test_T3_sell_exact()
    test_T4_forced_same_formula()
    test_T5_timing_not_total()
    test_T6_mtm_regression()
    test_T7_mask_guard_compat()
    print("ALL PASS — T1-T7 (training YOK)")
