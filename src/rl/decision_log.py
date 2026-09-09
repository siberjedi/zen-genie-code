"""Phase 4.17 — Decision Logging MVP (observability ONLY).

Env matematiğine DOKUNMAZ: bu modül env.step içine enjekte edilmez; train
döngüsünde bir OBSERVER olarak çağrılır (train-side injection). Böylece
env.py byte-aynı kalır, `env_hash` anlambilimi bozulmaz.

MVP satır başına tutulanlar (schema:1):
  run_id, config_id, seed, global_step, episode_id, timestamp_ms, candle_idx,
  obs_hash, action, action_probs, position, cash, equity, reward,
  cumulative_reward, regime,
  config_hash, env_hash, normalizer_hash, model_hash, dataset_hash

Raw observation SADECE hash (canonical_hash(round(obs,12)), 16 hex).
Full audit (raw+norm obs) HENÜZ yok.

Performans: buffered JSONL, append-only, default flush 4096 satır.
Kullanım (train döngüsü):
    lg = DecisionLogger(path, run_id="p47_E1", config_id="E1", seed=42,
                        config_hash=..., env_hash=..., normalizer_hash=...,
                        model_hash=..., dataset_hash=...)
    for step in steps:
        lg.log_step(global_step=step, episode_id=..., candle_idx=...,
                    obs=norm_obs, action=a, action_probs=probs,
                    position=pos, cash=cash, equity=eq_before,
                    reward=r, cumulative_reward=cum_r, regime="bull")
    lg.close()

Replay doğrulaması: her satırdaki obs_hash'i, candle_idx+normalizer+dataset ile
yeniden üretilen obs üzerinden karşılaştır; action/equity/reward dizileri ilgili
replay işleviyle eşitlenir. (Sentetik replay testi tests/test_decision_log.py)
"""
import json
import pathlib
import time

import numpy as np

from src.rl.determinism import canonical_hash

SCHEMA_VERSION = 1
DEFAULT_FLUSH = 4096
REQUIRED_FIELDS = {
    "schema", "run_id", "config_id", "seed", "global_step", "episode_id",
    "timestamp_ms", "candle_idx", "obs_hash", "action", "action_probs",
    "position", "cash", "equity", "reward", "cumulative_reward", "regime",
    "config_hash", "env_hash", "normalizer_hash", "model_hash", "dataset_hash",
}
ACTIONS = {0, 1, 2}


def obs_hash(obs) -> str:
    """canonical_hash(round(norm_obs, 12)) — 16 hex (repo convention)."""
    if isinstance(obs, np.ndarray):
        obs = obs.tolist()
    return canonical_hash(round(float(v), 12) for v in obs)


def dataset_hash(dates_like, closes_like, start: str, end: str) -> str:
    """Validation/candle penceresini pin'ler: (timestamp, OHLCV) satır hashi.

    canonical_hash ile aynı serileştirme prensibi; floats repr tabanlı, ts int.
    16 hex. Aynı pencere -> aynı hash; tek float değişimi -> farklı hash.
    """
    import pandas as pd
    dts = pd.to_datetime(np.asarray(dates_like), format="mixed", errors="coerce")
    closes = np.asarray(closes_like)
    mask = (dts >= pd.Timestamp(start)) & (dts <= pd.Timestamp(end))
    parts = []
    for ts, c in zip(dts[mask], closes[mask]):
        parts.append(int(ts.value))
        parts.append(round(float(c), 8))
    return canonical_hash(str(p) for p in parts)


def validate_line(d: dict) -> list:
    """Schema:1 doğrulama. Dönüş: hata mesajları listesi (boş = geçerli)."""
    errs = []
    missing = REQUIRED_FIELDS - set(d)
    if missing:
        errs.append(f"missing_fields={sorted(missing)}")
    if "schema" in d and d["schema"] != SCHEMA_VERSION:
        errs.append(f"schema={d['schema']} != {SCHEMA_VERSION}")
    for key in ("global_step", "candle_idx", "episode_id", "seed"):
        if key in d and not isinstance(d[key], int):
            errs.append(f"{key} not int")
    for key in ("cash", "equity", "reward", "cumulative_reward"):
        if key in d and not isinstance(d[key], (int, float)):
            errs.append(f"{key} not numeric")
    if "action" in d and d["action"] not in ACTIONS:
        errs.append(f"action={d['action']} not in {{0,1,2}}")
    if "position" in d and d["position"] not in {0, 1}:
        errs.append(f"position={d['position']} not in {{0,1}}")
    if "action_probs" in d and not isinstance(d["action_probs"], dict):
        errs.append("action_probs not dict")
    return errs


class DecisionLogger:
    """Buffered, append-only JSONL observer (train-side injection)."""

    def __init__(self, path, run_id, config_id, seed,
                 config_hash, env_hash, normalizer_hash, model_hash,
                 dataset_hash, flush_every: int = DEFAULT_FLUSH):
        self.path = pathlib.Path(path)
        self.run_id = run_id
        self.config_id = config_id
        self.seed = seed
        self.ids = {"config_hash": config_hash, "env_hash": env_hash,
                    "normalizer_hash": normalizer_hash, "model_hash": model_hash,
                    "dataset_hash": dataset_hash}
        self.flush_every = max(1, int(flush_every))
        self._buf = []
        self.rows = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", encoding="utf-8")
        header = {"schema_header": SCHEMA_VERSION, "run_id": run_id,
                  "config_id": config_id, "seed": seed, **self.ids}
        self._write_line(header)

    def _write_line(self, obj: dict) -> None:
        self._buf.append(json.dumps(obj, default=str))
        if len(self._buf) >= self.flush_every:
            self._flush()

    def _flush(self) -> None:
        if self._buf:
            self._fh.write("\n".join(self._buf) + "\n")
            self._buf.clear()

    def log_step(self, global_step, episode_id, candle_idx, obs, action,
                 action_probs, position, cash, equity, reward,
                 cumulative_reward, regime) -> None:
        self._write_line({
            "schema": SCHEMA_VERSION, "run_id": self.run_id,
            "config_id": self.config_id, "seed": self.seed,
            "global_step": int(global_step), "episode_id": int(episode_id),
            "timestamp_ms": int(time.time() * 1000), "candle_idx": int(candle_idx),
            "obs_hash": obs_hash(obs), "action": int(action),
            "action_probs": {str(k): float(v) for k, v in action_probs.items()},
            "position": int(position), "cash": round(float(cash), 8),
            "equity": round(float(equity), 8), "reward": round(float(reward), 8),
            "cumulative_reward": round(float(cumulative_reward), 8),
            "regime": str(regime), **self.ids,
        })
        self.rows += 1

    def close(self) -> None:
        self._flush()
        self._fh.write(json.dumps({"schema_trailer": SCHEMA_VERSION,
                                   "rows": self.rows,
                                   "run_id": self.run_id}) + "\n")
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def read_log(path):
    """JSONL okuyucu: (header, rows). Trailer atlanır."""
    header = None
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "schema_header" in obj:
                header = obj
            elif "schema_trailer" in obj:
                continue
            else:
                rows.append(obj)
    return header, rows