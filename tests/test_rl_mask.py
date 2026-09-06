"""Faz 4.11 — Mask doğruluk testleri (EĞİTİM YOK; scripted stepping).

Çalıştır: py -3 tests/test_rl_mask.py
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

import numpy as np
import pandas as pd

from src.rl.env import TradingEnv, ChunkedTradingEnv


def _seg(n=200, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({"date": pd.date_range("2021-01-01", periods=n, freq="5min"),
                         "open": close, "high": close + 0.5, "low": close - 0.5,
                         "close": close, "volume": 1.0})


def test_1_flat_mask():
    env = TradingEnv(_seg(), window=10)
    env.reset(seed=0)
    assert env.action_masks().tolist() == [True, True, False]
    print("PASS 1 flat -> BUY/HOLD only")


def test_2_long_mask():
    env = TradingEnv(_seg(), window=10)
    env.reset(seed=0)
    env.step(1)
    assert env.action_masks().tolist() == [True, False, True]
    print("PASS 2 long -> SELL/HOLD only")


def test_3_buy_transition():
    env = TradingEnv(_seg(), window=10)
    env.reset(seed=0)
    assert env.action_masks()[1] == np.True_
    env.step(1)
    m = env.action_masks()
    assert m.tolist() == [True, False, True] and m[1] == np.False_
    print("PASS 3 BUY sonrası LONG mask")


def test_4_sell_transition():
    env = TradingEnv(_seg(), window=10)
    env.reset(seed=0)
    env.step(1)
    env.step(2)
    assert env.action_masks().tolist() == [True, True, False]
    print("PASS 4 SELL sonrası FLAT mask")


def test_5_reset_chunk_boundary():
    env = ChunkedTradingEnv(_seg(12000), chunk_size=5000, window=10)
    for _ in range(4):
        env.reset(seed=0)
        assert env.action_masks().tolist() == [True, True, False]
    env.reset(seed=0)
    env.step(1)
    env.reset(seed=0)  # chunk sınırı reset'i de flat döndürmeli
    assert env.action_masks().tolist() == [True, True, False]
    print("PASS 5 reset/chunk boundary -> flat mask")


def test_6_forced_liquidation():
    env = TradingEnv(_seg(60), window=10)
    env.reset(seed=0)
    env.step(1)
    done, info = False, {}
    for _ in range(200):
        _, _, term, trunc, info = env.step(0)
        if term or trunc:
            done = True
            break
    assert done and info["forced_close"] is True
    assert env.action_masks().tolist() == [True, True, False]
    print("PASS 6 forced liquidation -> flat mask")


def test_7_deterministic_mask():
    outs = []
    for seed in (0, 1):
        env = TradingEnv(_seg(), window=10)
        env.reset(seed=seed)
        seq = [env.action_masks().tolist()]
        for a in (1, 0, 2, 0, 1):
            env.step(a)
            seq.append(env.action_masks().tolist())
        outs.append(seq)
    assert outs[0] == outs[1]  # mask state'in saf fonksiyonu
    print("PASS 7 deterministik mask (seed-bağımsız, state-bağımlı)")


def test_8_maskable_plumbing():
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.maskable.utils import is_masking_supported
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv
    venv = DummyVecEnv([lambda: Monitor(TradingEnv(_seg(300), window=10))])
    assert is_masking_supported(venv) is True
    model = MaskablePPO("MlpPolicy", venv, verbose=0)
    obs = venv.reset()
    for _ in range(5):
        mask = venv.env_method("action_masks")[0]
        action, _ = model.predict(obs, action_masks=mask, deterministic=True)
        action = int(action[0])
        assert bool(mask[action]) is True, "maskeli disi aksiyon!"
        obs, _, terms, truncs = venv.step([action])[:4]
        if bool(terms[0]) or bool(truncs[0]):
            break
    print("PASS 8 MaskablePPO plumbing (maskeli-disi aksiyon yok, egitim yok)")


if __name__ == "__main__":
    test_1_flat_mask()
    test_2_long_mask()
    test_3_buy_transition()
    test_4_sell_transition()
    test_5_reset_chunk_boundary()
    test_6_forced_liquidation()
    test_7_deterministic_mask()
    test_8_maskable_plumbing()
    print("ALL PASS — 8/8 (training YOK)")
