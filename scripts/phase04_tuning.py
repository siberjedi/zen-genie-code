"""Phase 4 tuning — ONAYLI koşum (2026-09-04).

Kilitli tasarım kararları (sonuç görülmeden):
- Grid: 4 PPO config (lr × n_steps/n_epochs varyasyonu), timesteps=600_000/koşu.
  Gerekçe: prob ~1224 step/sn → ~25-40 dk/koşu; 600k ≈ 1.9 train episode'u;
  12h cap bağlayıcı üst sınır olarak aktif. İlk tur 4/50 config (bütçe korunur).
- Seed'ler [42,7,123,2026,999], pair BTC/USDT (tek-pair limitasyon belgeli),
  fee 0.001, slippage 5bps, env v4.1.0 aynen.
- Seçim kuralı: mean validation Sharpe (5 seed); eşitlikte (±0.05) median,
  sonra std (küçük), sonra küçük config id. Final B'ye bakılmaz.
- SAC: Discrete env'de HARD ERROR verir (çalıştırılmaz).

Kullanım (parça parça, resume-safe):
  py -3 scripts/phase04_tuning.py --config-id C0 --seed 42
  py -3 scripts/phase04_tuning.py --all   # eksik koşumları tamamlar
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

from src.rl.train import (build_model, load_rl_data, seed_all, wallclock_callback,
                          write_run_metadata, HyperparamConfig, TimeoutExceeded,
                          load_experiment_config)
from src.rl.env import TradingEnv
from scripts.phase03_experiment import metrics_from_trades

RES_DIR = ROOT / "experiments" / "phase_04_rl" / "results"
MODEL_DIR = ROOT / "freqtrade" / "user_data" / "rl_models"
PAIR = "BTC/USDT"
SEEDS = [42, 7, 123, 2026, 999]
TIMESTEPS = 600_000
EVAL_SEED = 9999
VAL_DAYS = 181

GRID = {
    "C0": {"learning_rate": 3e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 10,
           "gamma": 0.99},
    "C1": {"learning_rate": 1e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 10,
           "gamma": 0.99},
    "C2": {"learning_rate": 3e-4, "n_steps": 4096, "batch_size": 128, "n_epochs": 10,
           "gamma": 0.99},
    "C3": {"learning_rate": 3e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 20,
           "gamma": 0.99},
}


def rollout_trades(model, df):
    """Deterministik rollout -> trade listesi + aksiyon/ekipman istatistikleri."""
    env = TradingEnv(df)
    obs, _ = env.reset(seed=EVAL_SEED)
    dates = pd.to_datetime(df["date"]).reset_index(drop=True)
    closes = df["close"].values
    cur = None
    trades, actions, equities = [], [], []
    prev_eq = 100.0  # giriş öncesi equity == deploy edilen stake (all-in, flat iken)
    done = False
    term_reason = "unknown"
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        action = int(action)
        actions.append(action)
        obs, rew, term, trunc, info = env.step(action)
        equities.append(info["equity"])
        pos = info["position"]
        if cur is None and pos == 1:
            t = len(actions) - 1
            cur = {"pair": PAIR, "open_date": dates[t], "open_rate": closes[t],
                   "stake_amount": prev_eq}
        prev_eq = info["equity"]
        if cur is not None and pos == 0:
            t = len(actions) - 1
            # stake = giriş anındaki equity (all-in): giriş adımının equity'si
            cur["close_date"] = dates[t]
            cur["close_rate"] = closes[t]
            trades.append(cur)
            cur = None
        if term:
            term_reason = "terminated_forced" if info["forced_close"] else "terminated"
            done = True
        if trunc:
            term_reason = "truncated_bankruptcy"
            done = True
    return trades, actions, equities, term_reason, info


def finalize_trades(raw, df):
    """Ham giriş/çıkış kayıtlarından fee/slippage'li P&L (env formülleriyle birebir)."""
    fee, slip = 0.001, 0.0005
    out = []
    for tr in raw:
        stake = tr["stake_amount"]
        amount = stake * (1 - fee) / (tr["open_rate"] * (1 + slip))
        proceeds = amount * tr["close_rate"] * (1 - slip) * (1 - fee)
        profit_abs = proceeds - stake
        fee_paid = stake * fee + amount * tr["close_rate"] * (1 - slip) * fee
        out.append({"pair": tr["pair"], "open_date": tr["open_date"],
                    "close_date": tr["close_date"], "open_rate": tr["open_rate"],
                    "close_rate": tr["close_rate"], "stake_amount": stake,
                    "profit_abs": profit_abs, "profit_ratio": profit_abs / stake,
                    "exit_reason": "rl_exit", "fee_paid": fee_paid})
    return out


def run_one(config_id, seed):
    out_json = RES_DIR / f"run_{config_id}_seed{seed}.json"
    if out_json.exists():
        print(f"[{config_id}/{seed}] atlanıyor (kayıtlı)", flush=True)
        return json.loads(out_json.read_text(encoding="utf-8"))
    hp = GRID[config_id]
    seed_all(seed)
    cfg_exp = load_experiment_config()
    train_df = load_rl_data(PAIR, "2020-01-01", "2022-12-31", "train", cfg_exp)
    val_df = load_rl_data(PAIR, "2023-01-01", "2023-06-30", "validation", cfg_exp)
    env = TradingEnv(train_df)
    hpc = HyperparamConfig(algo="PPO", seed=seed, total_timesteps=TIMESTEPS, **hp)
    model = build_model("PPO", env, seed,
                        learning_rate=hp["learning_rate"], n_steps=hp["n_steps"],
                        batch_size=hp["batch_size"], n_epochs=hp["n_epochs"],
                        gamma=hp["gamma"], verbose=0)
    t0 = time.time()
    model.learn(total_timesteps=TIMESTEPS, callback=wallclock_callback(12))
    dur = time.time() - t0
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    mpath = MODEL_DIR / f"phase4_{config_id}_seed{seed}.zip"
    model.save(str(mpath))
    mhash = hashlib.sha256(mpath.read_bytes()).hexdigest()[:16]
    # train rollout (episode reward/final equity)
    tr_raw, tr_act, tr_eq, tr_term, tr_info = rollout_trades(model, train_df)
    # validation rollout
    va_raw, va_act, va_eq, va_term, va_info = rollout_trades(model, val_df)
    va_trades = finalize_trades(va_raw, val_df)
    # bütünlük: trade P&L toplamı == final equity - 100
    assert abs(sum(t["profit_abs"] for t in va_trades) - (va_eq[-1] - 100.0)) < 0.05, \
        "P&L bütünlüğü bozuldu"
    met = metrics_from_trades(
        [{k: tr[k] for k in ("pair", "open_date", "close_date", "open_rate", "close_rate",
                             "stake_amount", "profit_abs", "profit_ratio")}
         for tr in va_trades], "2023-01-01", "2023-06-30")
    va = pd.DataFrame(va_trades)
    if len(va):
        va["open_date"] = pd.to_datetime(va["open_date"])
        va["close_date"] = pd.to_datetime(va["close_date"])
        holds = (va["close_date"] - va["open_date"]).dt.total_seconds() / 60
        flips = int((pd.Series(va_act).diff().fillna(0) != 0).sum())
    else:
        holds, flips = pd.Series([0]), 0
    res = {"config": config_id, "seed": seed, "hyperparams": hp,
           "timesteps": TIMESTEPS, "train_seconds": round(dur, 1),
           "train_ep_reward": round(float(np.log(tr_eq[-1] / 100.0)), 4),
           "train_final_equity": round(float(tr_eq[-1]), 2),
           "val": met, "val_term_reason": va_term,
           "val_actions": {int(a): int((np.array(va_act) == a).sum()) for a in (0, 1, 2)},
           "val_flips": flips,
           "val_med_hold_min": round(float(holds.median()), 1),
           "val_mean_hold_min": round(float(holds.mean()), 1),
           "val_fee_total": round(float(va["fee_paid"].sum()), 2) if len(va) else 0.0,
           "val_bankruptcy": bool("bankruptcy" in va_term),
           "model_path": str(mpath.relative_to(ROOT)), "model_hash": mhash}
    meta = write_run_metadata(
        RES_DIR / f"meta_{config_id}_seed{seed}.json", seed, "PPO", hpc, PAIR,
        "2020-01-01", "2022-12-31", list(TradingEnv(train_df).market_cols),
        100.0, 0.001, 5, dur,
        extra={"config_id": config_id, "validation": "2023-01-01->2023-06-30",
               "termination_val": va_term})
    res["metadata"] = str(meta) if isinstance(meta, str) else "meta_written"
    out_json.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    # ledger
    led_p = RES_DIR / "tuning_ledger.json"
    led = json.loads(led_p.read_text(encoding="utf-8")) if led_p.exists() else \
        {"planned_runs": 20, "planned_configs": 4, "completed": [], "hours_used": 0.0}
    led["completed"].append(f"{config_id}/{seed}")
    led["hours_used"] = round(led["hours_used"] + dur / 3600, 3)
    led_p.write_text(json.dumps(led, indent=2), encoding="utf-8")
    print(f"[{config_id}/{seed}] val sharpe={met['daily_sharpe']} net={met['net_abs']} "
          f"trades={met['trade_count']} ({dur/60:.0f}dk)", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config-id", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    RES_DIR.mkdir(parents=True, exist_ok=True)
    if args.all:
        for cid in GRID:
            for s in SEEDS:
                run_one(cid, s)
    else:
        run_one(args.config_id, args.seed)


if __name__ == "__main__":
    main()
