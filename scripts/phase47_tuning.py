"""Phase 4.7 FULL TUNING — ONAYLI koşum.

Kilitli tasarım (sonuç öncesi):
- Grid: 8 PPO config (ent_coef × lr; n_steps varyantı E7'de), 5 seed [42,7,123,2026,999].
  Gerekçe: Phase 4 (ent 0.0) + smoke (ent 0.01 keşif farkı) sonrası keşif ekseni
  ana belirsizlik; lr ikincil. 8/50 config (bütçe korunur).
- 600k step/koşu, chunk 5000, train-fit normalizer, fee 0.001, slippage 5bps,
  env v4.2.0 aynen, BTC/USDT, train 2020-22 / val 2023H1. Final B YOK.
- Seçim: mean validation Sharpe; tie (±0.05) → median → std(küçük) → küçük id.
- SAC çalıştırılmaz (Discrete env'de HARD ERROR — tasarım kararı).

Kullanım: py -3 scripts/phase47_tuning.py --config-id E0 --seed 42
Çıktılar: tuning47/ (run/meta/diag JSON — commitlenir) + modeller (untracked).
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
from stable_baselines3.common.monitor import Monitor

from src.rl.env import TradingEnv, ChunkedTradingEnv
from src.rl.normalize import FitNormalizer
from src.rl.gates import check_run
from src.rl.train import (build_model, load_rl_data, load_experiment_config,
                          seed_all, wallclock_callback, write_run_metadata,
                          HyperparamConfig, DiagnosticsCallback)
from scripts.phase03_experiment import metrics_from_trades

RES47 = ROOT / "experiments" / "phase_04_rl" / "tuning47"
MODEL47 = ROOT / "freqtrade" / "user_data" / "rl_models" / "phase47"
PAIR = "BTC/USDT"
SEEDS = [42, 7, 123, 2026, 999]
TIMESTEPS = 600_000
EVAL_SEED = 9999
VAL_DAYS = 181
FEE, SLIP = 0.001, 0.0005

GRID47 = {
    "E0": {"learning_rate": 3e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 10,
           "gamma": 0.99, "ent_coef": 0.0},
    "E1": {"learning_rate": 3e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 10,
           "gamma": 0.99, "ent_coef": 0.003},
    "E2": {"learning_rate": 3e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 10,
           "gamma": 0.99, "ent_coef": 0.01},
    "E3": {"learning_rate": 3e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 10,
           "gamma": 0.99, "ent_coef": 0.03},
    "E4": {"learning_rate": 1e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 10,
           "gamma": 0.99, "ent_coef": 0.0},
    "E5": {"learning_rate": 1e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 10,
           "gamma": 0.99, "ent_coef": 0.01},
    "E6": {"learning_rate": 1e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 10,
           "gamma": 0.99, "ent_coef": 0.03},
    "E7": {"learning_rate": 3e-4, "n_steps": 4096, "batch_size": 128, "n_epochs": 10,
           "gamma": 0.99, "ent_coef": 0.01},
}


def cost_split(open_rate, close_rate, stake):
    """fee/slippage/gross ayrımı (env formülleriyle birebir, saf hesap)."""
    amount = stake * (1 - FEE) / (open_rate * (1 + SLIP))
    fee = stake * FEE + amount * close_rate * (1 - SLIP) * FEE
    slip = amount * SLIP * (open_rate + close_rate)
    gross = amount * (close_rate - open_rate)
    return fee, slip, gross


def rollout_val(model, va_n, raw_close, raw_dates):
    env = TradingEnv(va_n, price_col="close_raw")
    obs, _ = env.reset(seed=EVAL_SEED)
    cur, trades, actions = None, [], []
    obs_finite, mvar_num, mvar_den, mvar_n = True, 0.0, 0.0, 0
    rews, nan_rew, eqs = [], False, []
    prev_eq = 100.0
    done = False
    while not done:
        v = obs[:, :-2]
        obs_finite = obs_finite and bool(np.isfinite(obs).all())
        mvar_num += float(v.sum())
        mvar_den += float((v ** 2).sum())
        mvar_n += v.size
        action, _ = model.predict(obs, deterministic=True)
        action = int(action)
        actions.append(action)
        obs, r, term, trunc, info = env.step(action)
        rews.append(float(r))
        eqs.append(float(info["equity"]))
        if not np.isfinite(r):
            nan_rew = True
        ci = env.t - 1
        if cur is None and info["position"] == 1:
            cur = {"pair": PAIR, "open_date": raw_dates[ci],
                   "open_rate": raw_close[ci], "stake_amount": prev_eq}
        if cur is not None and info["position"] == 0:
            cur["close_date"] = raw_dates[ci]
            cur["close_rate"] = raw_close[ci]
            trades.append(cur)
            cur = None
        prev_eq = info["equity"]
        done = term or trunc
    mean = mvar_num / mvar_n
    # profit_abs/gross/fee/slip tutarlılığı finalize ile aynı formülden gelir;
    # finalize_trades yerine doğrudan hesap (tek kaynak: cost_split)
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
                    "exit_reason": "rl_exit", "fee_paid": fee, "slip_paid": slip,
                    "gross": gross})
    return fin, actions, eqs, rews, info, {"finite": obs_finite,
                                               "market_var": mvar_den / mvar_n - mean ** 2,
                                               "nan_reward": nan_rew}


def run_one(config_id, seed):
    out_json = RES47 / f"run_{config_id}_seed{seed}.json"
    if out_json.exists():
        print(f"[{config_id}/{seed}] atlanıyor (kayıtlı)", flush=True)
        return json.loads(out_json.read_text(encoding="utf-8"))
    hp = GRID47[config_id]
    seed_all(seed)
    cfg_exp = load_experiment_config()
    train_df = load_rl_data(PAIR, "2020-01-01", "2022-12-31", "train", cfg_exp)
    val_df = load_rl_data(PAIR, "2023-01-01", "2023-06-30", "validation", cfg_exp)
    for _df in (train_df, val_df):
        _df["close_raw"] = _df["close"].values
    nz = FitNormalizer(["close", "volume"]).fit(train_df, "2020-01-01->2022-12-31")
    from src.rl.determinism import runtime_snapshot as _snap
    tr_n, va_n = nz.transform(train_df), nz.transform(val_df)
    env = ChunkedTradingEnv(tr_n, chunk_size=5000, window=30, price_col="close_raw")
    model = build_model("PPO", Monitor(env), seed, verbose=0, **hp)
    diag = RES47 / f"diag_{config_id}_seed{seed}.jsonl"
    t0 = time.time()
    model.learn(total_timesteps=TIMESTEPS,
                callback=[__import__("src.rl.train", fromlist=["DiagnosticsCallback"])
                          .DiagnosticsCallback(str(diag)),
                          wallclock_callback(12)])
    dur = time.time() - t0
    MODEL47.mkdir(parents=True, exist_ok=True)
    mpath = MODEL47 / f"p47_{config_id}_seed{seed}.zip"
    model.save(str(mpath))
    mhash = hashlib.sha256(mpath.read_bytes()).hexdigest()[:16]
    raw_dates = pd.to_datetime(val_df["date"]).reset_index(drop=True)
    raw_close = val_df["close"].values
    trades, acts, eqs, rews, info, obs_stat = rollout_val(model, va_n, raw_close, raw_dates)
    assert abs(sum(t["profit_abs"] for t in trades) - (eqs[-1] - 100.0)) < 0.05, \
        "P&L bütünlüğü bozuldu (trade toplamı != final equity - 100)"
    from src.rl.determinism import save_artifacts as _save_art
    art_hashes = _save_art(RES47 / f"art_{config_id}_seed{seed}.json", acts, eqs, rews)
    met = metrics_from_trades(
        [{k: tr[k] for k in ("pair", "open_date", "close_date", "open_rate", "close_rate",
                             "stake_amount", "profit_abs", "profit_ratio")}
         for tr in trades], "2023-01-01", "2023-06-30")
    tot_fee = float(sum(t["fee_paid"] for t in trades))
    tot_slip = float(sum(t["slip_paid"] for t in trades))
    tot_gross = float(sum(t["gross"] for t in trades))
    va = pd.DataFrame(trades)
    if len(va):
        va["open_date"] = pd.to_datetime(va["open_date"])
        va["close_date"] = pd.to_datetime(va["close_date"])
        holds = (va["close_date"] - va["open_date"]).dt.total_seconds() / 60
        flips = int((pd.Series(acts).diff().fillna(0) != 0).sum())
        med_hold, mean_hold = round(float(holds.median()), 1), round(float(holds.mean()), 1)
    else:
        flips, med_hold, mean_hold = 0, 0.0, 0.0
    term = "terminated_forced" if info["forced_close"] else "terminated"
    if "bankruptcy" in str(info):
        term = "truncated_bankruptcy"
    gate_in = {"trade_count": met["trade_count"],
               "actions": {int(a): int((np.array(acts) == a).sum()) for a in (0, 1, 2)},
               "invalid_actions": info["invalid_actions"], "total_steps": len(acts),
               "bankruptcy": "bankruptcy" in term, "nan_reward": False,
               "obs_var": obs_stat["market_var"], "fees_paid": tot_fee,
               "gross_profit": tot_gross, "max_dd": met["max_dd"], "timed_out": False,
               "exception": None, "n_days": VAL_DAYS}
    hpc = HyperparamConfig(algo="PPO", seed=seed, total_timesteps=TIMESTEPS, **hp)
    write_run_metadata(
        RES47 / f"meta_{config_id}_seed{seed}.json", seed, "PPO", hpc, PAIR,
        "2020-01-01", "2022-12-31", ["close", "volume"], 100.0, 0.001, 5, dur,
        extra={"phase": "4.7", "grid": config_id, "normalizer_hash": nz.artifact_hash(),
               "runtime": _snap(), "diagnostics": str(diag.name),
               "model_hash": mhash, "artifact_hashes": art_hashes,
               "gates": check_run(gate_in),
               "slippage_total": round(tot_slip, 2), "gross_total": round(tot_gross, 2),
               "termination_val": term,
               "val_actions": gate_in["actions"], "val_flips": flips,
               "val_med_hold_min": med_hold, "val_mean_hold_min": mean_hold})
    res = {"config": config_id, "seed": seed, "hyperparams": hp, "timesteps": TIMESTEPS,
           "train_seconds": round(dur, 1), "val": met, "val_term_reason": term,
           "val_actions": gate_in["actions"], "val_flips": flips,
           "val_med_hold_min": med_hold, "val_mean_hold_min": mean_hold,
           "val_fee_total": round(tot_fee, 2), "val_slip_total": round(tot_slip, 2),
           "val_gross_total": round(tot_gross, 2),
           "val_bankruptcy": "bankruptcy" in term, "model_hash": mhash,
           "gates": check_run(gate_in)}
    out_json.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    led_p = RES47 / "ledger47.json"
    led = json.loads(led_p.read_text(encoding="utf-8")) if led_p.exists() else \
        {"planned_runs": 40, "planned_configs": 8, "completed": [], "hours_used": 0.0}
    led["completed"].append(f"{config_id}/{seed}")
    led["hours_used"] = round(led["hours_used"] + dur / 3600, 3)
    led_p.write_text(json.dumps(led, indent=2), encoding="utf-8")
    print(f"[{config_id}/{seed}] sharpe={met['daily_sharpe']} net={met['net_abs']} "
          f"n={met['trade_count']} acts={gate_in['actions']} ({dur/60:.0f}dk)", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config-id", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    RES47.mkdir(parents=True, exist_ok=True)
    if args.all:
        for cid in GRID47:
            for s in SEEDS:
                run_one(cid, s)
    else:
        run_one(args.config_id, args.seed)


if __name__ == "__main__":
    main()
