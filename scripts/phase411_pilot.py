"""Phase 4.11 MASKING PILOT — ONAYLI koşum (2 configs x 5 seeds = 10).

B1 = E1 mirror (ent 0.003, lr 3e-4, n2048/batch64/epochs10/gamma .99).
B2 = entropy varyanti (ent 0.01, gerisi E1 ile birebir).
Kilitli: 600k step, chunk 5000, train-fit normalizer, fee 0.001, slippage 5bps,
env v4.2.0 + action_masks, BTC/USDT, train 2020-22 / val 2023H1, seedler ayni.
Maske DISINDA hicbir sey degismedi. Final B YOK.
MaskablePPO + DummyVecEnv + masked rollout (invalid orneklenemez).
"""
import argparse
import hashlib
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from sb3_contrib import MaskablePPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

from src.rl.env import TradingEnv, ChunkedTradingEnv
from src.rl.normalize import FitNormalizer
from src.rl.gates import check_run
from src.rl.train import (load_rl_data, load_experiment_config, seed_all,
                          wallclock_callback, write_run_metadata,
                          HyperparamConfig, DiagnosticsCallback)
from scripts.phase47_tuning import cost_split
from scripts.phase03_experiment import metrics_from_trades

RES = ROOT / "experiments" / "phase_04_rl" / "pilot411"
MODELDIR = ROOT / "freqtrade" / "user_data" / "rl_models" / "phase411"
PAIR = "BTC/USDT"
SEEDS = [42, 7, 123, 2026, 999]
TIMESTEPS = 600_000
VAL_DAYS = 181
FEE, SLIP = 0.001, 0.0005

GRID = {
    "B1": {"learning_rate": 3e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 10,
           "gamma": 0.99, "ent_coef": 0.003},
    "B2": {"learning_rate": 3e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 10,
           "gamma": 0.99, "ent_coef": 0.01},
}


def rollout_masked(model, va_n, raw_close, raw_dates):
    """Maskeli deterministik rollout. Maskesiz aksiyon orneklenirse ABORT sayaci artar."""
    env = TradingEnv(va_n, price_col="close_raw")
    obs, _ = env.reset(seed=9999)
    cur, trades, actions = None, [], []
    eqs, rews, nan_rew = [], [], False
    v = va_n[[c for c in va_n.columns if c not in ("date", "open", "high", "low", "close_raw")]]
    obs_var = float(v.values.var())
    masked_violations = 0
    prev_eq = 100.0
    done = False
    while not done:
        mask = env.action_masks()
        action, _ = model.predict(obs, action_masks=mask, deterministic=True)
        action = int(action)
        if not bool(mask[action]):
            masked_violations += 1
        actions.append(action)
        obs, r, term, trunc, info = env.step(action)
        eqs.append(float(info["equity"]))
        rews.append(float(r))
        if not np.isfinite(r):
            nan_rew = True
        ci = env.t - 1
        if cur is None and info["position"] == 1:
            cur = {"pair": PAIR, "open_date": raw_dates[ci],
                   "open_rate": raw_close[ci], "stake_amount": prev_eq}
        if cur is not None and info["position"] == 0:
            fforced = bool(term and info.get("forced_close"))
            fci = len(raw_dates) - 1 if fforced else ci
            cur["close_date"] = raw_dates[fci]
            cur["close_rate"] = raw_close[fci]
            cur["forced"] = fforced
            trades.append(cur)
            cur = None
        prev_eq = info["equity"]
        done = term or trunc
    return trades, actions, eqs, rews, info, masked_violations, obs_var, nan_rew


def run_one(config_id, seed):
    out_json = RES / f"run_{config_id}_seed{seed}.json"
    if out_json.exists():
        print(f"[{config_id}/{seed}] atlaniyor (kayitli)", flush=True)
        return json.loads(out_json.read_text(encoding="utf-8"))
    hp = GRID[config_id]
    seed_all(seed)
    cfg_exp = load_experiment_config()
    train_df = load_rl_data(PAIR, "2020-01-01", "2022-12-31", "train", cfg_exp)
    val_df = load_rl_data(PAIR, "2023-01-01", "2023-06-30", "validation", cfg_exp)
    for _df in (train_df, val_df):
        _df["close_raw"] = _df["close"].values
    nz = FitNormalizer(["close", "volume"]).fit(train_df, "2020-01-01->2022-12-31")
    from src.rl.determinism import runtime_snapshot as _snap
    tr_n, va_n = nz.transform(train_df), nz.transform(val_df)
    venv = DummyVecEnv([lambda: Monitor(
        ChunkedTradingEnv(tr_n, chunk_size=5000, window=30, price_col="close_raw"))])
    model = MaskablePPO("MlpPolicy", venv, seed=seed, verbose=0, **hp)
    diag = RES / f"diag_{config_id}_seed{seed}.jsonl"
    t0 = time.time()
    model.learn(total_timesteps=TIMESTEPS,
                callback=[DiagnosticsCallback(str(diag)), wallclock_callback(12)])
    dur = time.time() - t0
    MODELDIR.mkdir(parents=True, exist_ok=True)
    mpath = MODELDIR / f"p411_{config_id}_seed{seed}.zip"
    model.save(str(mpath))
    mhash = hashlib.sha256(mpath.read_bytes()).hexdigest()[:16]
    raw_dates = pd.to_datetime(val_df["date"]).reset_index(drop=True)
    raw_close = val_df["close"].values
    trades, acts, eqs, rews, info, violations, obs_var, nan_rew = rollout_masked(
        model, va_n, raw_close, raw_dates)
    assert violations == 0, f"maske ihlali: {violations}"
    fin = []
    for tr in trades:
        fee, slip, gross = cost_split(tr["open_rate"], tr["close_rate"], tr["stake_amount"])
        stake = tr["stake_amount"]
        amount = stake * (1 - FEE) / (tr["open_rate"] * (1 + SLIP))
        proceeds = amount * tr["close_rate"] * (1 - SLIP) * (1 - FEE)
        profit_abs = proceeds - stake
        fin.append({"pair": tr["pair"], "open_date": tr["open_date"],
                    "close_date": tr["close_date"], "open_rate": tr["open_rate"],
                    "close_rate": tr["close_rate"], "stake_amount": stake,
                    "profit_abs": profit_abs, "profit_ratio": profit_abs / stake,
                    "exit_reason": "forced_close" if tr.get("forced") else "rl_exit",
                    "fee_paid": fee, "slip_paid": slip, "gross": gross})
    assert abs(sum(t["profit_abs"] for t in fin) - (eqs[-1] - 100.0)) < 0.05, \
        "P&L bütünlüğü bozuldu (trade toplamı != final equity - 100)"
    met = metrics_from_trades(
        [{k: tr[k] for k in ("pair", "open_date", "close_date", "open_rate", "close_rate",
                             "stake_amount", "profit_abs", "profit_ratio")}
         for tr in fin], "2023-01-01", "2023-06-30")
    # butunluk: env equity ile trade toplami (ayni pencerede deterministik rollout)
    venv2 = TradingEnv(va_n, price_col="close_raw")
    _o, _ = venv2.reset(seed=9999)
    for _a in acts:
        _o, _, _t, _tr, _i = venv2.step(_a)
        if _t or _tr:
            break
    assert abs(sum(t["profit_abs"] for t in fin) - (_i["equity"] - 100.0)) < 0.05
    tot_fee = float(sum(t["fee_paid"] for t in fin))
    tot_slip = float(sum(t["slip_paid"] for t in fin))
    tot_gross = float(sum(t["gross"] for t in fin))
    va = pd.DataFrame(fin)
    if len(va):
        va["open_date"] = pd.to_datetime(va["open_date"])
        va["close_date"] = pd.to_datetime(va["close_date"])
        holds = (va["close_date"] - va["open_date"]).dt.total_seconds() / 60
        flips = int((pd.Series(acts).diff().fillna(0) != 0).sum())
        med_hold, mean_hold = round(float(holds.median()), 1), round(float(holds.mean()), 1)
    else:
        flips, med_hold, mean_hold = 0, 0.0, 0.0
    term = "terminated_forced" if info["forced_close"] else "terminated"
    gate_in = {"trade_count": met["trade_count"],
               "actions": {int(a): int((np.array(acts) == a).sum()) for a in (0, 1, 2)},
               "invalid_actions": 0, "total_steps": len(acts),
               "bankruptcy": "bankruptcy" in term, "nan_reward": nan_rew,
               "obs_var": obs_var, "fees_paid": tot_fee,
               "gross_profit": tot_gross, "max_dd": met["max_dd"], "timed_out": False,
               "exception": None, "n_days": VAL_DAYS}
    hpc = HyperparamConfig(algo="MaskablePPO", seed=seed, total_timesteps=TIMESTEPS, **hp)
    write_run_metadata(
        RES / f"meta_{config_id}_seed{seed}.json", seed, "MaskablePPO", hpc, PAIR,
        "2020-01-01", "2022-12-31", ["close", "volume"], 100.0, 0.001, 5, dur,
        extra={"phase": "4.11", "grid": config_id, "normalizer_hash": nz.artifact_hash(),
               "runtime": _snap(), "diagnostics": str(diag.name),
               "model_hash": mhash, "gates": check_run(gate_in),
               "masked_eval": True, "mask_violations": violations,
               "slippage_total": round(tot_slip, 2), "gross_total": round(tot_gross, 2),
               "termination_val": term, "val_actions": gate_in["actions"],
               "val_flips": flips, "val_med_hold_min": med_hold,
               "val_mean_hold_min": mean_hold})
    from src.rl.determinism import save_artifacts as _save_art
    art_hashes = _save_art(RES / f"art_{config_id}_seed{seed}.json", acts, eqs, rews)
    res = {"config": config_id, "seed": seed, "hyperparams": hp, "timesteps": TIMESTEPS,
           "train_seconds": round(dur, 1), "val": met, "val_term_reason": term,
           "val_actions": gate_in["actions"], "val_flips": flips,
           "val_med_hold_min": med_hold, "val_mean_hold_min": mean_hold,
           "val_fee_total": round(tot_fee, 2), "val_slip_total": round(tot_slip, 2),
           "val_gross_total": round(tot_gross, 2), "val_invalid_rate": 0.0,
           "val_mask_violations": violations,
           "val_bankruptcy": "bankruptcy" in term, "model_hash": mhash,
           "artifact_hashes": art_hashes, "gates": check_run(gate_in)}
    out_json.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    led_p = RES / "ledger411.json"
    led = json.loads(led_p.read_text(encoding="utf-8")) if led_p.exists() else \
        {"planned_runs": 10, "planned_configs": 2, "completed": [], "hours_used": 0.0}
    led["completed"].append(f"{config_id}/{seed}")
    led["hours_used"] = round(led["hours_used"] + dur / 3600, 3)
    led_p.write_text(json.dumps(led, indent=2), encoding="utf-8")
    print(f"[{config_id}/{seed}] sharpe={met['daily_sharpe']} net={met['net_abs']} "
          f"n={met['trade_count']} invalid=0 ({dur/60:.0f}dk)", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config-id", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)
    if args.all:
        for cid in GRID:
            for s in SEEDS:
                run_one(cid, s)
    else:
        run_one(args.config_id, args.seed)


if __name__ == "__main__":
    main()
