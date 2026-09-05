"""Faz 4.1 — Budget runner + loader (bu görevde EĞİTİM ÇALIŞTIRILMAZ).

- `--config` GERÇEKTEN okunur (rl_budget + splitler).
- Loader: feather yerleşim, ZORUNLU tarih filtresi, train/val rolü config
  penceresine bağlı, Final Test B HARD ERROR.
- Bütçe: max 50 config × 5 seed, config başına 12h wall-clock cap (callback ile
  zorlanır), ledger ile muhasebe. hardcoded 100k KALDIRILDI.
- Algoritma: PPO→PPO, SAC→SAC denemesi discrete env'de HARD ERROR (SAC sürekli
  action ister; sessiz fallback YOK). Bilinmeyen algo → HARD ERROR.
- Reproducibility: seed_all + model seed + metadata.
- B10: tek-pair (BTC default); protokol multi-pair şart koşmuyor, değişiklik yok.
"""
import argparse
import hashlib
import itertools
import json
import pathlib
import random
import subprocess
import time
from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd
import yaml

from src.rl.env import TradingEnv, ENV_VERSION

ROOT = pathlib.Path(__file__).parents[2]
DEFAULT_CONFIG = ROOT / "config" / "experiment.yaml"
DATA_DIR = ROOT / "freqtrade" / "user_data" / "data" / "binance"
DEFAULT_TIMESTEPS = 500_000  # yapısal varsayılan; bağlayıcı sınır 12h cap'tir


class FinalTestLeakError(AssertionError):
    """Final Test dönemine erişim denemesi."""


class UnsupportedAlgorithmError(ValueError):
    """Desteklenmeyen algo/env kombinasyonu (sessiz fallback YOK)."""


class BudgetExceededError(ValueError):
    """50 config üst sınırı aşıldı."""


class RoleWindowError(ValueError):
    """Rol penceresi config aralığının dışında."""


@dataclass
class HyperparamConfig:
    algo: str = "PPO"
    seed: int = 42
    total_timesteps: int = DEFAULT_TIMESTEPS
    learning_rate: float = 3e-4
    n_steps: int = 2048
    batch_size: int = 64
    n_epochs: int = 10
    gamma: float = 0.99
    ent_coef: float = 0.0  # Faz 4.4: exploration parametrizasyonu (shaping değil)


def load_experiment_config(path=DEFAULT_CONFIG) -> dict:
    return yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))


def _parse_window(s: str):
    s = s.split("#")[0]
    a, b = [x.strip().split()[0] for x in s.split("→")]
    return pd.Timestamp(a), pd.Timestamp(b)


def split_windows(cfg: dict) -> dict:
    sp = cfg["splits"]["phase_04_rl"]
    out = {}
    for k in ("train", "validation", "final_test_B"):
        out[k] = _parse_window(sp[k])
    return out


def load_rl_data(pair: str, start, end, role: str,
                 cfg: dict | None = None) -> pd.DataFrame:
    """Feather loader + ZORUNLU filtre + rol penceresi + Final B guard."""
    cfg = cfg or load_experiment_config()
    wins = split_windows(cfg)
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    fb0, fb1 = wins["final_test_B"]
    if not (end < fb0 or start > fb1):
        raise FinalTestLeakError(
            f"Final Test B [{fb0.date()}->{fb1.date()}] ile örtüşme: {start.date()}->{end.date()}")
    if role in ("train", "validation"):
        w0, w1 = wins[role]
        if not (start >= w0 and end <= w1):
            raise RoleWindowError(
                f"{role} penceresi {w0.date()}->{w1.date()} dışında: {start.date()}->{end.date()}")
    elif role != "final_eval":
        raise ValueError(f"bilinmeyen rol: {role} (train/validation/final_eval)")
    fp = DATA_DIR / f"{pair.replace('/', '_')}-5m.feather"
    if not fp.exists():
        raise FileNotFoundError(f"veri yok: {fp}")
    df = pd.read_feather(fp)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)
    m = (df["date"] >= start) & (df["date"] <= end)
    if not m.any():
        raise ValueError(f"{pair} için {start.date()}->{end.date()} aralığında veri yok")
    return df.loc[m].reset_index(drop=True)


def build_model(algo: str, env: TradingEnv, seed: int, **hyperparams):
    """Sessiz fallback YOK: SAC discrete env'de HARD ERROR."""
    if algo == "PPO":
        from stable_baselines3 import PPO
        hyperparams = dict(hyperparams)
        verbose = hyperparams.pop("verbose", 1)
        return PPO("MlpPolicy", env, seed=seed, verbose=verbose, **hyperparams)
    if algo == "SAC":
        raise UnsupportedAlgorithmError(
            "SAC sürekli action space ister; TradingEnv Discrete(3). "
            "Box-action env protokol değişikliği gerektirir — yapılmadı.")
    raise UnsupportedAlgorithmError(f"desteklenmeyen algo: {algo} (PPO/SAC)")


def seed_all(seed: int) -> int:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        pass
    return seed


def config_hash(cfg: HyperparamConfig) -> str:
    return hashlib.sha256(json.dumps(asdict(cfg), sort_keys=True).encode()).hexdigest()[:16]


def env_hash() -> str:
    return hashlib.sha256((pathlib.Path(__file__).parent / "env.py").read_bytes()
                          ).hexdigest()[:16]


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                                       text=True).strip()
    except Exception:
        return "unknown"


def write_run_metadata(path, seed: int, algo: str, cfg: HyperparamConfig,
                       pair: str, start, end, feature_list: list,
                       initial_capital: float, fee: float, slippage_bps: float,
                       duration_s: float | None, extra: dict | None = None) -> dict:
    import datetime
    meta = {"seed": seed, "algorithm": algo, "config_hash": config_hash(cfg),
            "hyperparams": asdict(cfg), "pair": pair,
            "data_range": f"{pd.Timestamp(start).date()}->{pd.Timestamp(end).date()}",
            "feature_list": feature_list, "environment_version": ENV_VERSION,
            "environment_hash": env_hash(), "git_commit": git_commit(),
            "timestamp": datetime.datetime.now().astimezone().isoformat(),
            "training_duration_s": duration_s, "initial_capital": initial_capital,
            "fee": fee, "slippage_bps": slippage_bps}
    if extra:
        meta.update(extra)
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


class TimeoutExceeded(TimeoutError):
    pass


class DiagnosticsCallback:
    """Rollout-başı PPO/sb3 metrikleri + aksiyon histogramı → JSONL.

    Kaynak: SB3 logger snapshot (loss/entropy/KL/clip/EV/LR, mevcutsa) +
    rollout/episode sayaçları. Monitor sarmalanmış env'lerde episode
    reward/length de logger'a düşer. Training ÇALIŞTIRMAZ, sadece kaydeder.
    """

    def __new__(cls, out_path, verbose=0):
        from stable_baselines3.common.callbacks import BaseCallback
        import numpy as np

        class _Diag(BaseCallback):
            def __init__(self):
                super().__init__(verbose)
                self.out_path = pathlib.Path(out_path)
                self.rows = []
                self._acts = []

            def _on_step(self) -> bool:
                a = self.locals.get("actions")
                if a is not None:
                    self._acts.extend(np.asarray(a).ravel().tolist())
                return True

            def _on_rollout_end(self) -> None:
                snap = {}
                for k, v in self.logger.name_to_value.items():
                    try:
                        snap[f"log_{k}"] = float(v)
                    except (TypeError, ValueError):
                        snap[f"log_{k}"] = str(v)
                arr = np.array(self._acts, dtype=int) if self._acts else np.array([], dtype=int)
                snap["actions"] = {str(x): int((arr == x).sum()) for x in (0, 1, 2)}
                snap["n_steps"] = len(arr)
                self.rows.append(snap)
                self._acts = []

            def _on_training_end(self) -> None:
                self.out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.out_path, "w", encoding="utf-8") as f:
                    for i, r in enumerate(self.rows):
                        f.write(json.dumps({"rollout": i, **r}) + "\n")
        return _Diag()


def wallclock_callback(limit_hours: float):
    """12h cap callback fabrikası (SB3 BaseCallback; training YOK testte sahte saatle)."""
    from stable_baselines3.common.callbacks import BaseCallback

    class _WallClock(BaseCallback):
        def __init__(self):
            super().__init__()
            self.t0 = time.time()

        def _on_step(self) -> bool:
            if time.time() - self.t0 > limit_hours * 3600:
                raise TimeoutExceeded(f"{limit_hours}h cap aşıldı")
            return True
    return _WallClock()


def build_grid(param_lists: dict, seeds: list, cfg_exp: dict) -> list:
    """Kartezyen grid + 50 config cap + 5 seed cap."""
    max_c = int(cfg_exp["rl_budget"]["max_configs"])
    max_s = int(cfg_exp["rl_budget"]["max_seeds"])
    if len(seeds) > max_s:
        raise BudgetExceededError(f"seed {len(seeds)} > max {max_s}")
    keys = sorted(param_lists)
    combos = list(itertools.product(*[param_lists[k] for k in keys]))
    if len(combos) > max_c:
        raise BudgetExceededError(f"config {len(combos)} > max {max_c}")
    runs = []
    for combo in combos:
        hp = dict(zip(keys, combo))
        for s in seeds:
            runs.append(HyperparamConfig(seed=s, **hp))
    return runs


def budget_ledger(runs: list, per_config_hours: float) -> dict:
    cfgs = {(r.algo, r.total_timesteps, r.learning_rate, r.n_steps,
             r.batch_size, r.n_epochs, r.gamma) for r in runs}
    return {"n_runs": len(runs), "n_configs": len(cfgs),
            "n_seeds": len({r.seed for r in runs}),
            "per_config_hours": per_config_hours,
            "max_total_hours": round(len(cfgs) * per_config_hours, 2)}


def plan(algo="PPO", pair="BTC/USDT", role="train", seeds=(42,),
         param_lists=None, config_path=DEFAULT_CONFIG) -> dict:
    """Eğitimsiz plan + bütçe muhasebesi (testler ve --dry-run bunu kullanır)."""
    cfg_exp = load_experiment_config(config_path)
    wins = split_windows(cfg_exp)
    w0, w1 = wins[role] if role in wins else (None, None)
    param_lists = param_lists or {}
    base = {"algo": [algo]}
    base.update(param_lists)
    runs = build_grid(base, list(seeds), cfg_exp)
    per_h = float(cfg_exp["rl_budget"]["max_train_hours"])  # kilitli 12h cap
    return {"runs": runs, "window": (str(w0.date()), str(w1.date())) if w0 else None,
            "ledger": budget_ledger(runs, per_h), "role": role, "pair": pair}


def run_all(dry_run=True, **kw):
    p = plan(**kw)
    print(f"plan: {p['ledger']['n_runs']} run, {p['ledger']['n_configs']} config, "
          f"cap {p['ledger']['max_total_hours']}h (dry_run={dry_run})")
    if dry_run:
        return p
    raise NotImplementedError("execute yolu bu görevde çağrılmaz (tuning yok)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--pair", default="BTC/USDT")
    ap.add_argument("--role", default="train", choices=["train", "validation"])
    ap.add_argument("--algo", default="PPO", choices=["PPO", "SAC"])
    ap.add_argument("--seeds", nargs="*", type=int, default=[42])
    ap.add_argument("--execute", action="store_true",
                    help="GERÇEK eğitim (bu görevde KULLANMA)")
    args = ap.parse_args()
    if args.execute:
        raise SystemExit("execute bu görevde kilitli (tuning yok)")
    run_all(dry_run=True, algo=args.algo, pair=args.pair, role=args.role,
            seeds=args.seeds, config_path=args.config)


if __name__ == "__main__":
    main()
