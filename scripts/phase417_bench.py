"""Phase 4.17 — Logging overhead benchmark (MVP, buffered JSONL).

Training YOK; sentetik veriyle logging eklemenin step başına maliyetini ölçer.
Çalıştır: py -3 scripts/phase417_bench.py
"""
import math
import pathlib
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from src.rl.decision_log import DecisionLogger, obs_hash  # noqa: E402

N_STEPS = 51794           # val 2023H1 adımlarıyla aynı büyüklük
WINDOW = 30
FEE, SLIP = 0.001, 0.0005

DUM = {"config_hash": "cfgh" * 4, "env_hash": "envh" * 4,
       "normalizer_hash": "nrmz" * 4, "model_hash": "mdlh" * 4,
       "dataset_hash": "dats" * 4}


def _closes(n):
    return [100.0 + 6.0 * math.sin(i / 13.0) + i * 0.012 for i in range(n)]


def _policy(obs):
    last, prev = obs[-1], obs[-3]
    return 1 if last > prev else (2 if last < prev else 0)


def _probs(a):
    return {0: 0.9, 1: 0.05, 2: 0.05} if a == 0 else \
        ({0: 0.05, 1: 0.9, 2: 0.05} if a == 1 else {0: 0.05, 1: 0.05, 2: 0.9})


def run_loop(closes, n_steps, log: bool, path=None):
    eq = prev_eq = 100.0
    pos = False
    amt = 0.0
    cum = 0.0
    t0 = time.perf_counter()
    if log:
        lg = DecisionLogger(path, run_id="bench", config_id="bench", seed=1,
                            flush_every=4096, **DUM)
    try:
        for k in range(n_steps):
            c = WINDOW + k
            obs = closes[c - WINDOW:c]
            a = _policy(obs)
            if not pos and a == 1:
                amt = eq * (1 - FEE) / (closes[c] * (1 + SLIP))
                pos = True
            elif pos and a == 2:
                eq = amt * closes[c] * (1 - SLIP) * (1 - FEE)
                pos = False
            if pos:
                eq = amt * closes[c]
            reward = eq - prev_eq
            prev_eq = eq
            cum += reward
            if log:
                lg.log_step(global_step=k, episode_id=0, candle_idx=c, obs=obs,
                            action=a, action_probs=_probs(a), position=int(pos),
                            cash=0.0 if pos else eq, equity=eq, reward=reward,
                            cumulative_reward=cum, regime="bull")
    finally:
        if log:
            lg.close()
    dt = time.perf_counter() - t0
    return dt, eq, cum


def main():
    closes = _closes(N_STEPS + WINDOW)
    dt_off, eq_off, cum_off = run_loop(closes, N_STEPS, log=False)
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / "bench.jsonl"
        dt_on, eq_on, cum_on = run_loop(closes, N_STEPS, log=True, path=p)
        size_mb = p.stat().st_size / 1e6
        n_lines = sum(1 for _ in open(p, encoding="utf-8"))
    per_off = dt_off / N_STEPS * 1e6
    per_on = dt_on / N_STEPS * 1e6
    print(f"steps        : {N_STEPS}")
    print(f"logging OFF  : {dt_off:7.3f}s  ({per_off:6.3f} us/step)  eq={eq_off:.4f}")
    print(f"logging ON   : {dt_on:7.3f}s  ({per_on:6.3f} us/step)  eq={eq_on:.4f}")
    print(f"overhead     : +{per_on - per_off:6.3f} us/step  (%{(per_on / max(per_off, 1e-12) - 1) * 100:+.1f})")
    print(f"file size    : {size_mb:.2f} MB  ({n_lines} lines incl header+trailer)")


if __name__ == "__main__":
    main()