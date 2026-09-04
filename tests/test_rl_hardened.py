"""Faz 4.1 — Hardening testleri (EĞİTİM YOK, 12 test).

Çalıştır: py -3 tests/test_rl_hardened.py
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

import numpy as np
import pandas as pd

from src.rl.env import TradingEnv, ENV_VERSION, PositionInconsistencyError


def _synth(n=200, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({"date": pd.date_range("2021-01-01", periods=n, freq="5min"),
                         "open": close, "high": close + 0.5, "low": close - 0.5,
                         "close": close, "volume": rng.uniform(10, 100, n)})


def test_1_imports():
    import gymnasium, stable_baselines3, torch
    print(f"PASS 1 imports (gymnasium {gymnasium.__version__}, "
          f"sb3 {stable_baselines3.__version__})")


def test_2_reset_step_smoke():
    env = TradingEnv(_synth(), window=30)
    obs, info = env.reset(seed=0)
    assert obs.shape == (30, len(env.market_cols) + 2), obs.shape
    assert obs.dtype == np.float32
    steps = 0
    done = False
    while not done and steps < 500:
        obs, rew, term, trunc, info = env.step(0)
        assert obs.shape == (30, len(env.market_cols) + 2)
        assert set(info) >= {"equity", "position", "invalid_actions", "roundtrips",
                             "fees_paid", "forced_close", "drawdown"}
        done = term or trunc
        steps += 1
    assert done, "episode bitmedi"
    print(f"PASS 2 reset/step smoke ({steps} adım, obs {obs.shape})")


def test_3_action_transitions():
    env = TradingEnv(_synth(), window=5)
    env.reset(seed=1)
    assert env.pos_hist[-1] == 0
    env.step(1)  # buy
    assert env.amount > 0 and env.entries == 1
    n_inv = env.invalid_actions
    env.step(1)  # buy while long -> no-op
    assert env.amount > 0 and env.invalid_actions == n_inv + 1
    env.step(2)  # sell
    assert env.amount == 0 and env.roundtrips == 1
    n_inv = env.invalid_actions
    env.step(2)  # sell while flat -> no-op
    assert env.invalid_actions == n_inv + 1
    print("PASS 3 action transitions (buy/sell/invalid no-op)")


def test_4_fee_slippage_math():
    # bağımsız el hesabı: fee=0.001, slip=5bps, buy@100 sell@110, cash=100
    df = pd.DataFrame({"date": pd.date_range("2021-01-01", periods=10, freq="5min"),
                       "open": 100.0, "high": 110.0, "low": 100.0,
                       "close": [100.0] * 3 + [110.0] * 7, "volume": 1.0})
    env = TradingEnv(df, fee=0.001, slippage_bps=5, window=2, initial_capital=100.0)
    env.reset(seed=0)
    env.step(1)  # buy @100 -> exec 100.05
    exp_amount = 100 * 0.999 / 100.05
    assert abs(env.amount - exp_amount) < 1e-9, env.amount
    assert abs(env.fees_paid - 0.1) < 1e-9
    env.step(2)  # sell @110 -> exec 109.945
    exp_proc = exp_amount * 109.945
    exp_fee = exp_proc * 0.001
    assert abs(env.cash - (exp_proc - exp_fee)) < 1e-9, env.cash
    assert abs(env.fees_paid - (0.1 + exp_fee)) < 1e-9
    # sıfır maliyet varyantı: reward == log(1.1)
    env0 = TradingEnv(df, fee=0.0, slippage_bps=0, window=2, initial_capital=100.0)
    env0.reset(seed=0)
    _, r1, _, _, _ = env0.step(1)
    assert r1 == 0.0  # sadece pozisyon açıldı, portföy değişmedi
    _, r2, _, _, _ = env0.step(2)
    assert abs(r2 - np.log(1.1)) < 1e-9, r2
    print("PASS 4 fee/slippage hesabı (el hesabıyla birebir)")


def test_5_episode_end_forced():
    env = TradingEnv(_synth(40), window=5)
    env.reset(seed=0)
    _, r0, _, _, _ = env.step(1)  # aç ve tut (ilk reward da toplama dahil)
    total, done, steps = r0, False, 0
    while not done and steps < 100:
        _, r, term, trunc, info = env.step(0)
        total += r
        done = term or trunc
        steps += 1
    assert done and info["forced_close"] is True, info
    assert env.amount == 0  # sessiz düşürme YOK, execute edildi
    assert abs(total - np.log(info["equity"] / 100.0)) < 1e-9  # exact ayrışım
    print("PASS 5 episode-end forced liquidation (sessiz drop yok)")


def test_6_date_isolation():
    from src.rl.train import load_rl_data
    tr = load_rl_data("BTC/USDT", "2020-01-01", "2022-12-31", "train")
    va = load_rl_data("BTC/USDT", "2023-01-01", "2023-06-30", "validation")
    assert tr["date"].max() <= pd.Timestamp("2022-12-31")
    assert va["date"].min() >= pd.Timestamp("2023-01-01")
    assert va["date"].max() <= pd.Timestamp("2023-06-30")
    assert tr["date"].max() < va["date"].min()
    print(f"PASS 6 date isolation (train {len(tr)} / val {len(va)} satır, örtüşme yok)")


def test_7_final_b_guard():
    from src.rl.train import load_rl_data, split_windows, load_experiment_config, FinalTestLeakError
    cfg = load_experiment_config()
    w = split_windows(cfg)
    assert w["final_test_B"] == (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-06-30"))
    for role in ("train", "validation"):
        try:
            load_rl_data("XXX/YYY", "2024-02-01", "2024-03-01", role)
            raise SystemExit("guard yakalamalıydı")
        except FinalTestLeakError:
            pass
    try:
        load_rl_data("BTC/USDT", "2023-07-01", "2023-08-01", "train")
        raise SystemExit("rol penceresi yakalamalıydı")
    except Exception as e:
        assert "RoleWindowError" in type(e).__name__, type(e)
    print("PASS 7 Final Test B guard (HARD ERROR) + rol penceresi")


def test_8_seed_determinism():
    from src.rl.train import seed_all
    seed_all(123)
    a = np.random.rand(3)
    seed_all(123)
    b = np.random.rand(3)
    assert (a == b).all()
    acts = [1, 0, 0, 2, 0, 1, 2, 0] * 5
    outs = []
    for _ in range(2):
        env = TradingEnv(_synth(), window=10)
        env.reset(seed=7)
        seq = [env.step(x) for x in acts]
        outs.append([(o[0].tobytes(), o[1], o[4]["equity"]) for o in seq])
    assert outs[0] == outs[1], "aynı seed+aksiyon farklı sonuç veremez"
    print("PASS 8 seed determinism (env + numpy)")


def test_9_invalid_risk_guards():
    env = TradingEnv(_synth(), window=5)
    env.reset(seed=0)
    n = env.invalid_actions
    env.step(99)  # geçersiz action -> hold + sayaç
    assert env.invalid_actions == n + 1
    env.cash, env.amount = 0.0, 0.0  # çöküş senaryosu
    _, _, _, trunc, _ = env.step(0)
    assert trunc is True  # bankruptcy guard
    # invariant 300 rastgele aksiyonda hiç bozulmamalı
    env2 = TradingEnv(_synth(500), window=10)
    env2.reset(seed=0)
    rng = np.random.default_rng(0)
    for a in rng.integers(0, 3, 300):
        env2.step(int(a))  # PositionInconsistencyError fırlatırsa test patlar
    print("PASS 9 invalid/risk guardlar (sayaç, bankruptcy truncate, invariant)")


def test_10_algo_selection():
    from src.rl.train import build_model, UnsupportedAlgorithmError
    env = TradingEnv(_synth(120), window=10)
    env.reset(seed=0)
    m = build_model("PPO", env, seed=0, n_steps=64, verbose=0)
    assert type(m).__name__ == "PPO"
    for bad in ("SAC", "TD3", "DQN"):
        try:
            build_model(bad, env, seed=0)
            raise SystemExit(f"{bad} yakalamalıydı")
        except UnsupportedAlgorithmError:
            pass
    print("PASS 10 algo selection (PPO ok, SAC/bilinmeyen HARD ERROR, fallback yok)")


def test_11_config_loading():
    from src.rl.train import load_experiment_config, HyperparamConfig, DEFAULT_TIMESTEPS
    cfg = load_experiment_config()
    assert (cfg["rl_budget"]["max_configs"], cfg["rl_budget"]["max_seeds"],
            cfg["rl_budget"]["max_train_hours"]) == (50, 5, 12)
    assert cfg["rl_budget"]["algorithms"] == ["PPO", "SAC"]
    assert HyperparamConfig().total_timesteps == DEFAULT_TIMESTEPS != 100_000
    print("PASS 11 config loading (50×5×12h okunuyor, 100k gitti)")


def test_12_budget_accounting():
    from src.rl.train import build_grid, budget_ledger, BudgetExceededError
    cfg = {"rl_budget": {"max_configs": 50, "max_seeds": 5, "max_train_hours": 12}}
    try:
        build_grid({"learning_rate": [float(x) for x in range(51)]}, [0], cfg)
        raise SystemExit("51 config yakalamalıydı")
    except BudgetExceededError:
        pass
    try:
        build_grid({"learning_rate": [1e-4]}, list(range(6)), cfg)
        raise SystemExit("6 seed yakalamalıydı")
    except BudgetExceededError:
        pass
    runs = build_grid({"learning_rate": [1e-4, 3e-4]}, [0, 1, 2], cfg)
    led = budget_ledger(runs, 12)
    assert (led["n_runs"], led["n_configs"], led["n_seeds"],
            led["max_total_hours"]) == (6, 2, 3, 24), led
    print("PASS 12 budget accounting (cap + ledger matematiği)")


if __name__ == "__main__":
    test_1_imports()
    test_2_reset_step_smoke()
    test_3_action_transitions()
    test_4_fee_slippage_math()
    test_5_episode_end_forced()
    test_6_date_isolation()
    test_7_final_b_guard()
    test_8_seed_determinism()
    test_9_invalid_risk_guards()
    test_10_algo_selection()
    test_11_config_loading()
    test_12_budget_accounting()
    print("ALL PASS — 12/12 (training YOK)")
