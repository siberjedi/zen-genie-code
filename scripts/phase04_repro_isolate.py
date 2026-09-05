"""REPRO FAIL kök-neden izolasyonu (diagnostic, tuning DEĞİL).

Tiny PPO (512 step, sentetik env): aynı-seed eğitimi 2 kez koşturup ağırlık
hash'lerini karşılaştırır. Çıktı: weight hash + torch thread bilgisi.
Kullanım:
  $env:PYTHONHASHSEED='0'; py -3 scripts/phase04_repro_isolate.py --tag X
"""
import argparse
import os
import sys

print("PYTHONHASHSEED=" + str(os.environ.get("PYTHONHASHSEED")), flush=True)
sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from src.rl.train import build_model, seed_all
from src.rl.env import TradingEnv


def tiny_train(seed: int) -> str:
    seed_all(seed)
    import torch
    print("torch threads:", torch.get_num_threads(), flush=True)
    rng = np.random.default_rng(0)
    close = 100 + np.cumsum(rng.normal(0, 1, 600))
    df = pd.DataFrame({"date": pd.date_range("2021-01-01", periods=600, freq="5min"),
                       "open": close, "high": close + 0.5, "low": close - 0.5,
                       "close": close, "volume": 1.0})
    env = TradingEnv(df, window=10)
    model = build_model("PPO", env, seed, n_steps=128, verbose=0)
    model.learn(total_timesteps=512)
    import hashlib

    def _leaves(_o):
        if isinstance(_o, dict):
            for _k in sorted(_o):
                yield from _leaves(_o[_k])
        else:
            try:
                yield np.ascontiguousarray(_o.detach().cpu().numpy())
            except AttributeError:
                yield np.ascontiguousarray(_o)
    h = hashlib.sha256()
    for _arr in _leaves(model.get_parameters()):
        h.update(_arr.tobytes())
    return h.hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="X")
    ap.add_argument("--repeat", type=int, default=1,
                    help="aynı süreçte kaç kez (carryover testi)")
    args = ap.parse_args()
    for i in range(args.repeat):
        print(f"[{args.tag}.{i}] weights=", tiny_train(42), flush=True)


if __name__ == "__main__":
    main()
