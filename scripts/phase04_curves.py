"""Phase 4 curve/trade extraction — INFERENCE ONLY (eğitim yok, tuning yok).

Dondurulmuş modellerle deterministic val rollout tekrarı; equity eğrisi +
trade listesi kaydeder. Mevcut run_*.json dosyalarına DOKUNMAZ (ayrı dosya yazar).
Final B'ye dokunmaz.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from stable_baselines3 import PPO
from src.rl.train import load_rl_data, load_experiment_config, seed_all
from src.rl.env import TradingEnv
from scripts.phase04_tuning import rollout_trades, finalize_trades, EVAL_SEED

RES_DIR = ROOT / "experiments" / "phase_04_rl" / "results"
MODEL_DIR = ROOT / "freqtrade" / "user_data" / "rl_models"
CFG_IDS = ["C0", "C1", "C2", "C3"]
SEEDS = [42, 7, 123, 2026, 999]


def main():
    cfg_exp = load_experiment_config()
    val_df = load_rl_data("BTC/USDT", "2023-01-01", "2023-06-30", "validation", cfg_exp)
    for cid in CFG_IDS:
        for s in SEEDS:
            out = RES_DIR / f"curves_{cid}_seed{s}.json"
            if out.exists():
                print(f"[{cid}/{s}] atlanıyor (kayıtlı)", flush=True)
                continue
            seed_all(s)
            model = PPO.load(str(MODEL_DIR / f"phase4_{cid}_seed{s}.zip"))
            raw, acts, eqs, term, info = rollout_trades(model, val_df)
            trades = finalize_trades(raw, val_df)
            dates = pd.to_datetime(val_df["date"]).dt.strftime("%Y-%m-%dT%H:%M:%S").tolist()
            out.write_text(json.dumps({
                "config": cid, "seed": s,
                "equity_curve": [round(float(x), 4) for x in eqs],
                "curve_start": dates[0], "curve_end": dates[-1],
                "termination": term, "forced_close": bool(info["forced_close"]),
                "bankruptcy": bool("bankruptcy" in term),
                "train_ep_reward_note": "egitim sonu degerleri run_*.json'da",
                "trades": [{k: (str(v) if "date" in k else v) for k, v in tr.items()}
                           for tr in trades],
            }, indent=1), encoding="utf-8")
            print(f"[{cid}/{s}] trades={len(trades)} eq_end={eqs[-1]:.2f} {term}",
                  flush=True)


if __name__ == "__main__":
    main()
