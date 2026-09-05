"""Faz 4.6 — Repro probe (YETKİLİ mini-eğitim, 1 config × seed42 × 2 tekrar).

Amaç: aynı seed/config/data davranış tekrarlanabilirliği (performans YOK).
Kısa budget: 20,480 step, chunked(5000) + train-fit normalizer, ent 0.0.
Final B: dokunulmaz (assert edilir, indirilmez).
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("PYTHONHASHSEED", "0")

import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from stable_baselines3.common.monitor import Monitor

from src.rl.env import ChunkedTradingEnv, TradingEnv
from src.rl.normalize import FitNormalizer
from src.rl.determinism import (apply_thread_limits, deterministic_mode,
                                canonical_hash, save_artifacts, runtime_snapshot)
from src.rl.train import (build_model, load_rl_data, load_experiment_config,
                          seed_all, wallclock_callback, HyperparamConfig)

PROBE_DIR = ROOT / "experiments" / "phase_04_rl" / "probe"
HP = {"learning_rate": 3e-4, "n_steps": 2048, "batch_size": 64,
      "n_epochs": 10, "gamma": 0.99, "ent_coef": 0.0}
STEPS = 20_480
SEED = 42


def one_run(tag: str) -> dict:
    seed_all(SEED)
    cfg_exp = load_experiment_config()
    tr = load_rl_data("BTC/USDT", "2020-01-01", "2022-12-31", "train", cfg_exp)
    va = load_rl_data("BTC/USDT", "2023-01-01", "2023-06-30", "validation", cfg_exp)
    assert tr["date"].max() < pd.Timestamp("2024-01-01")
    assert va["date"].max() < pd.Timestamp("2024-01-01")
    for _df in (tr, va):
        _df["close_raw"] = _df["close"].values
    nz = FitNormalizer(["close", "volume"]).fit(tr, "2020-01-01->2022-12-31")
    tr_n, va_n = nz.transform(tr), nz.transform(va)
    env = ChunkedTradingEnv(tr_n, chunk_size=5000, window=30, price_col="close_raw")
    model = build_model("PPO", Monitor(env), SEED, verbose=0, **HP)
    t0 = time.time()
    model.learn(total_timesteps=STEPS, callback=wallclock_callback(12))
    dur = time.time() - t0
    # val rollout (deterministik)
    venv = TradingEnv(va_n, price_col="close_raw")
    obs, _ = venv.reset(seed=9999)
    raw_dates = pd.to_datetime(va["date"]).reset_index(drop=True)
    raw_close = va["close"].values
    acts, eqs, rews, cur, trades = [], [], [], None, []
    prev_eq, done = 100.0, False
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        acts.append(int(a))
        obs, r, term, trunc, info = venv.step(int(a))
        eqs.append(info["equity"])
        rews.append(float(r))
        ci = venv.t - 1
        if cur is None and info["position"] == 1:
            cur = {"open_date": str(raw_dates[ci]), "open_rate": float(raw_close[ci]),
                   "stake_amount": prev_eq}
        if cur is not None and info["position"] == 0:
            cur.update({"close_date": str(raw_dates[ci]),
                        "close_rate": float(raw_close[ci])})
            trades.append(cur)
            cur = None
        prev_eq = info["equity"]
        done = term or trunc
    # ağırlık hash'i (determinism.hash_model_weights — container-safe)
    from src.rl.determinism import hash_model_weights
    model_hash = hash_model_weights(model.get_parameters())
    art = save_artifacts(PROBE_DIR / f"artifacts_{tag}.json", acts, eqs, rews)
    art["model_hash"] = model_hash
    # chunk/val boundary kaydı
    bounds = [(str(tr["date"].iloc[s]), str(tr["date"].iloc[e - 1]))
              for s, e in env.bounds]
    return {"tag": tag, "seconds": round(dur, 1),
            "model_hash": model_hash, "artifacts": art,
            "n_trades": len(trades),
            "chunk_bounds": bounds, "val_range": [str(va["date"].min()), str(va["date"].max())],
            "runtime": runtime_snapshot()}


def main():
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    apply_thread_limits(1)
    deterministic_mode()
    a = one_run("A")
    (PROBE_DIR / "probe_A.json").write_text(json.dumps(a, indent=2), encoding="utf-8")
    b = one_run("B")
    (PROBE_DIR / "probe_B.json").write_text(json.dumps(b, indent=2), encoding="utf-8")
    keys = ["model_hash"]
    rep = {"model_same": a["model_hash"] == b["model_hash"],
           "actions_same": a["artifacts"]["actions"] == b["artifacts"]["actions"],
           "equities_same": a["artifacts"]["equities"] == b["artifacts"]["equities"],
           "rewards_same": a["artifacts"]["rewards"] == b["artifacts"]["rewards"],
           "trades_same": a["n_trades"] == b["n_trades"],
           "bounds_same": a["chunk_bounds"] == b["chunk_bounds"],
           "val_range_same": a["val_range"] == b["val_range"]}
    rep["REPRO"] = "PASS" if all(rep.values()) else "FAIL"
    (PROBE_DIR / "probe_compare.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=2), flush=True)
    print(f"A: {a['seconds']}sn trades={a['n_trades']} model={a['model_hash']}", flush=True)
    print(f"B: {b['seconds']}sn trades={b['n_trades']} model={b['model_hash']}", flush=True)


if __name__ == "__main__":
    main()
