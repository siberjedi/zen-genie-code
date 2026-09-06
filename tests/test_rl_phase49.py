"""Faz 4.9 — Muhasebe bütünlük testleri (EĞİTİM YOK; scripted stepping + saf fonksiyonlar).

Çalıştır: py -3 tests/test_rl_phase49.py
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

import numpy as np
import pandas as pd

from src.rl.env import TradingEnv
from src.rl.gates import action_breakdown, sample_flag


def _seg(n=60, seed=0, start=100.0):
    rng = np.random.default_rng(seed)
    close = start + np.cumsum(rng.normal(0, 1, n))
    df = pd.DataFrame({"date": pd.date_range("2021-01-01", periods=n, freq="5min"),
                       "open": close, "high": close + 0.5, "low": close - 0.5,
                       "close": close, "volume": 1.0})
    df["close_raw"] = df["close"].values
    return df


class _Scripted:
    """Sabit aksiyon dizisi döndüren sahte model (eğitim YOK)."""

    def __init__(self, actions):
        self.actions = list(actions)
        self.k = 0

    def predict(self, obs, deterministic=True):
        a = self.actions[min(self.k, len(self.actions) - 1)]
        self.k += 1
        return a, None


def _recorded_trades(df, actions):
    """phase04_tuning.rollout_trades ile AYNI kayıt mantığı (forced=sun mum)."""
    from scripts.phase04_tuning import rollout_trades
    return rollout_trades(_Scripted(actions), df)


def test_1_forced_candle_index():
    df = _seg(60)
    trades, *_ = _recorded_trades(df, [1] + [0] * 200)
    assert len(trades) == 1, trades
    tr = trades[0]
    assert str(tr["close_date"]) == str(df["date"].iloc[-1]), (tr["close_date"], df["date"].iloc[-1])
    assert tr.get("forced") is True
    print("PASS 1 forced candle/index = son mum")


def test_2_forced_price():
    df = _seg(60)
    trades, *_ = _recorded_trades(df, [1] + [0] * 200)
    assert abs(trades[0]["close_rate"] - float(df["close"].iloc[-1])) < 1e-12
    # sinyal çıkışı ise bu adımın mumu olmalı (forced DEĞİL)
    trades2, *_ = _recorded_trades(df, [1, 2] + [0] * 200)
    assert trades2[0].get("forced") is not True
    print("PASS 2 forced price = final close; sinyal çıkışı ayrı")


def test_3_ledger_equity():
    from scripts.phase04_tuning import finalize_trades
    df = _seg(80)
    raw, *_rest = _recorded_trades(df, [1, 2, 1, 2] + [0] * 300)
    assert len(raw) == 2
    fin = finalize_trades(raw, df)
    # bağımsız env equity hesabı (AYNI window=30; recorder default ile eşleşmeli)
    env = TradingEnv(df, window=30)
    env.reset(seed=0)
    for a in [1, 2, 1, 2] + [0] * 300:
        _, _, term, trunc, info = env.step(a)
        if term or trunc:
            break
    assert abs(sum(t["profit_abs"] for t in fin) - (info["equity"] - 100.0)) < 0.05
    print("PASS 3 ledger <-> equity reconciliation")


def test_4_reward_equity():
    env = TradingEnv(_seg(80), window=10)
    env.reset(seed=0)
    tot, done, k = 0.0, False, 0
    acts = [1, 0, 0, 2] + [0] * 300
    while not done and k < 400:
        _, r, term, trunc, info = env.step(acts[min(k, len(acts) - 1)])
        assert np.isfinite(r)
        tot += r
        done = term or trunc
        k += 1
    assert abs(tot - np.log(info["equity"] / 100.0)) < 1e-9
    print("PASS 4 reward <-> equity reconciliation (telescoping exact)")


def test_5_classification():
    acts = [0, 1, 1, 2, 2, 0, 5, 1]
    poss = [0, 0, 1, 1, 0, 0, 0, 1]
    bd = action_breakdown(acts, poss)
    assert bd["valid_HOLD"] == 2 and bd["valid_BUY"] == 1 and bd["valid_SELL"] == 1
    assert bd["invalid_SELL_while_flat"] == 1 and bd["invalid_BUY_while_long"] == 2
    assert bd["invalid_other"] == 1  # aksiyon 5
    assert abs(sum(bd["rates"].values()) - 1.0) < 1e-9
    print("PASS 5 valid/invalid classification (6 sınıf)")


def test_6_partition_reconcile():
    tr = [{"profit": 10.0, "forced": False, "fee": 1.0, "slip": 0.5, "gross": 11.5, "stake": 100.0},
          {"profit": -4.0, "forced": False, "fee": 1.0, "slip": 0.5, "gross": -2.5, "stake": 100.0},
          {"profit": 22.0, "forced": True, "fee": 0.3, "slip": 0.2, "gross": 22.5, "stake": 100.0}]
    nf = [t for t in tr if not t["forced"]]
    ff = [t for t in tr if t["forced"]]
    assert abs((sum(t["profit"] for t in nf) + sum(t["profit"] for t in ff))
               - sum(t["profit"] for t in tr)) < 1e-9
    print("PASS 6 forced/non-forced partition reconciles")


def test_7_small_n():
    assert sample_flag(0) == "EXTREME SMALL-N"
    assert sample_flag(9) == "EXTREME SMALL-N"
    assert sample_flag(10) == "VERY SMALL-N"
    assert sample_flag(19) == "VERY SMALL-N"
    assert sample_flag(20) == "SMALL-N"
    assert sample_flag(49) == "SMALL-N"
    assert sample_flag(50) == "normal"
    assert sample_flag(500) == "normal"
    print("PASS 7 small-N sınırları (9/10, 19/20, 49/50)")


if __name__ == "__main__":
    test_1_forced_candle_index()
    test_2_forced_price()
    test_3_ledger_equity()
    test_4_reward_equity()
    test_5_classification()
    test_6_partition_reconcile()
    test_7_small_n()
    print("ALL PASS — 7/7 (training YOK)")
