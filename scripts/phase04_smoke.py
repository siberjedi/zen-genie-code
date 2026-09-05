"""Faz 4.4 — Smoke training (ALTYAPI doğrulama, performans YORUMU YOK).

Kilitli smoke config: C0-tabanı + ent_coef=0.01 (diagnostic duyarlılık için;
seçim DEĞİL) + total_timesteps=20_480 (~4 chunk-episode) + seed 42, 7.
Train: chunked(5000) + train-fit normalizer + Monitor + diagnostics.
Val: tam-pencere deterministik rollout (karşılaştırılabilir metrik).
Final B: YOK (loader guard + assert). Sonuç "başarılı" diye YORUMLANMAZ.
"""
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
                          HyperparamConfig)
from scripts.phase04_tuning import finalize_trades
from scripts.phase03_experiment import metrics_from_trades


def rollout_smoke(model, norm_df, raw_df):
    """Deterministik rollout: obs normalizeli env'den, fiyatlar ham çerçeveden
    (satır sırası birebir korunur). Trade muhasebesi finalize_trades ile."""
    import hashlib
    env = TradingEnv(norm_df, price_col="close_raw")
    obs, _ = env.reset(seed=9999)
    raw_dates = pd.to_datetime(raw_df["date"]).reset_index(drop=True)
    raw_close = raw_df["close"].values
    cur, trades, actions = None, [], []
    obs_finite, obs_sum, obs_sq, obs_n = True, 0.0, 0.0, 0
    prev_eq = 100.0
    done = False
    while not done:
        obs_finite = obs_finite and bool(np.isfinite(obs).all())
        obs_sum += float(obs[:, :-2].sum())
        obs_sq += float((obs[:, :-2] ** 2).sum())
        obs_n += obs[:, :-2].size
        action, _ = model.predict(obs, deterministic=True)
        action = int(action)
        actions.append(action)
        obs, _, term, trunc, info = env.step(action)
        ci = env.t - 1
        if cur is None and info["position"] == 1:
            cur = {"pair": "BTC/USDT", "open_date": raw_dates[ci],
                   "open_rate": raw_close[ci], "stake_amount": prev_eq}
        if cur is not None and info["position"] == 0:
            cur["close_date"] = raw_dates[ci]
            cur["close_rate"] = raw_close[ci]
            trades.append(cur)
            cur = None
        prev_eq = info["equity"]
        done = term or trunc
    mean = obs_sum / obs_n
    var = obs_sq / obs_n - mean ** 2
    obs_stat = {"finite": obs_finite, "market_var": var}
    return trades, actions, info, obs_stat

SMOKE_DIR = ROOT / "experiments" / "phase_04_rl" / "smoke"
NORM_DIR = ROOT / "freqtrade" / "user_data" / "rl_norm"
SEEDS = [42, 7]
SMOKE_STEPS = 20_480
HP = {"learning_rate": 3e-4, "n_steps": 2048, "batch_size": 64,
      "n_epochs": 10, "gamma": 0.99, "ent_coef": 0.01}


def run_seed(seed: int) -> dict:
    seed_all(seed)
    cfg_exp = load_experiment_config()
    train_df = load_rl_data("BTC/USDT", "2020-01-01", "2022-12-31", "train", cfg_exp)
    val_df = load_rl_data("BTC/USDT", "2023-01-01", "2023-06-30", "validation", cfg_exp)
    assert train_df["date"].max() < pd.Timestamp("2024-01-01")
    assert val_df["date"].max() < pd.Timestamp("2024-01-01")
    for _df in (train_df, val_df):
        _df["close_raw"] = _df["close"].values
    norm = FitNormalizer(["close", "volume"]).fit(train_df, "2020-01-01->2022-12-31")
    npath = NORM_DIR / "smoke_norm.json"
    nhash = norm.save(npath)
    tr_n = norm.transform(train_df)
    va_n = norm.transform(val_df)
    assert "close_raw" in tr_n.columns  # ham fiyat korunur (execution için)
    # normalizer doğruluk (manuel recompute)
    manual = (val_df["close"].iloc[0] - train_df["close"].mean()) / train_df["close"].std(ddof=1)
    assert abs(va_n["close"].iloc[0] - manual) < 1e-9
    env = ChunkedTradingEnv(tr_n, chunk_size=5000, window=30, price_col="close_raw")
    menv = Monitor(env)
    model = build_model("PPO", menv, seed, verbose=0, **HP)
    diag = ROOT / "experiments" / "phase_04_rl" / "smoke" / f"diag_seed{seed}.jsonl"
    t0 = time.time()
    model.learn(total_timesteps=SMOKE_STEPS,
                callback=[__import__("src.rl.train", fromlist=["DiagnosticsCallback"])
                          .DiagnosticsCallback(str(diag)),
                          wallclock_callback(12)])
    dur = time.time() - t0
    # val rollout (tam-pencere, frozen metodoloji; fiyatlar ham)
    trades_raw, acts, info, obs_stat = rollout_smoke(model, va_n, val_df)
    assert obs_stat["finite"], "obs'ta non-finite değer"
    assert obs_stat["market_var"] > 0, "market obs varyansı 0 (sabit obs)"
    term = "terminated_forced" if info["forced_close"] else "terminated"
    trades = finalize_trades(trades_raw, va_n)
    met = metrics_from_trades(
        [{k: tr[k] for k in ("pair", "open_date", "close_date", "open_rate", "close_rate",
                             "stake_amount", "profit_abs", "profit_ratio")}
         for tr in trades], "2023-01-01", "2023-06-30")
    hpc = HyperparamConfig(algo="PPO", seed=seed, total_timesteps=SMOKE_STEPS, **HP)
    meta = write_run_metadata(
        SMOKE_DIR / f"meta_seed{seed}.json", seed, "PPO", hpc, "BTC/USDT",
        "2020-01-01", "2022-12-31", ["close", "volume"], 100.0, 0.001, 5, dur,
        extra={"smoke": True, "normalizer_hash": nhash,
               "diagnostics": str(diag.relative_to(ROOT)),
               "validation": "2023-01-01->2023-06-30", "val_metrics": met,
               "val_term_reason": term,
                "val_actions": {int(a): int((np.array(acts) == a).sum()) for a in (0, 1, 2)}})
    import hashlib as _hl
    def _leaves(_o):
        if isinstance(_o, dict):
            for _k in sorted(_o):
                yield from _leaves(_o[_k])
        else:
            try:
                yield np.ascontiguousarray(_o.detach().cpu().numpy())
            except AttributeError:
                yield np.ascontiguousarray(_o)
    h = _hl.sha256()
    for _arr in _leaves(model.get_parameters()):
        h.update(_arr.tobytes())
    return {"seed": seed, "seconds": round(dur, 1), "val": met, "term": term,
            "actions": {int(a): int((np.array(acts) == a).sum()) for a in (0, 1, 2)},
            "obs_stat": obs_stat, "weights_hash": h.hexdigest()[:16]}


def main():
    SMOKE_DIR.mkdir(parents=True, exist_ok=True)
    rec = {}
    for s in SEEDS:
        rec[s] = run_seed(s)
        print(f"[smoke seed {s}] {rec[s]['seconds']}sn val_trades={rec[s]['val']['trade_count']} "
              f"net={rec[s]['val']['net_abs']} sharpe={rec[s]['val']['daily_sharpe']} "
              f"acts={rec[s]['actions']} ({rec[s]['term']})", flush=True)
    # determinizm: seed 42 tekrarı — ağırlık hash'i + val metrikleri aynı olmalı
    rep = run_seed(42)
    same = (rep["weights_hash"] == rec[42]["weights_hash"]
            and rep["val"] == rec[42]["val"])
    print(f"determinizm tekrarı: weights_hash eşit={rep['weights_hash'] == rec[42]['weights_hash']} "
          f"val-metrik eşitliği={rep['val'] == rec[42]['val']}", flush=True)
    (SMOKE_DIR / "smoke_summary.json").write_text(
        json.dumps({"seeds": rec, "repeat42_equal": bool(same),
                    "note": "infra-only; performans yorumu YOK"}, indent=2, default=str),
        encoding="utf-8")


if __name__ == "__main__":
    main()
