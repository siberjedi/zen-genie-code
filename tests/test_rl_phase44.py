"""Faz 4.4 — Hardening testleri (EĞİTİM YOK; diagnostics testi mini-learn içerir).

Çalıştır: py -3 tests/test_rl_phase44.py
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

import numpy as np
import pandas as pd

from src.rl.env import TradingEnv, ChunkedTradingEnv, CHUNK_SIZE, ENV_VERSION
from src.rl.normalize import FitNormalizer
from src.rl.gates import check_run
from src.rl.train import HyperparamConfig, TimeoutExceeded, wallclock_callback


def _synth(n=3000, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({"date": pd.date_range("2021-01-01", periods=n, freq="5min"),
                         "open": close, "high": close + 0.5, "low": close - 0.5,
                         "close": close, "volume": rng.uniform(10, 100, n)})


def test_1_chunk_bounds():
    assert ENV_VERSION == "4.2.0"
    assert CHUNK_SIZE == 5000
    env = ChunkedTradingEnv(_synth(12000), chunk_size=5000, window=30)
    assert len(env.bounds) == 3  # 5000+5000+2000
    assert env.bounds[0] == (0, 5000) and env.bounds[2] == (10000, 12000)
    seen = [env.reset(seed=0)[1]["chunk"]]
    for _ in range(4):
        seen.append(env.reset(seed=0)[1]["chunk"])
    # NOT: constructor iç reset ile chunk 0'ı tüketir; ilk explicit reset -> 1
    assert seen == [1, 2, 0, 1, 2], seen  # deterministik rotasyon
    try:
        ChunkedTradingEnv(_synth(20), chunk_size=5000, window=30)
        raise SystemExit("kısa veri yakalamalıydı")
    except ValueError:
        pass
    try:
        ChunkedTradingEnv(_synth(5000), chunk_size=100, window=30)
        raise SystemExit("küçük chunk yakalamalıydı")
    except ValueError:
        pass
    print("PASS 1 chunk bounds + deterministik rotasyon")


def test_2_chunk_no_silent_drop():
    env = ChunkedTradingEnv(_synth(6000), chunk_size=5000, window=10)
    env.reset(seed=0)
    env.step(1)  # aç
    total, done, n = 0.0, False, 0
    while not done and n < 6000:
        _, r, term, trunc, info = env.step(0)
        total += r
        done = term or trunc
        n += 1
    assert done and info["forced_close"] is True
    assert env.amount == 0  # likide edildi, düşürülmedi
    print("PASS 2 chunk-sonu forced liquidation (sessiz drop yok)")


def test_3_normalizer():
    df = _synth(1000)
    tr, va = df.iloc[:700], df.iloc[700:]
    nz = FitNormalizer(["close", "volume"]).fit(tr, "2021-train")
    assert abs(nz.transform(tr)["close"].mean()) < 1e-9  # train ort ~0
    # val, TRAIN istatistiğiyle dönüşür (val istatistiği kullanılmaz)
    manual = (va["close"].iloc[0] - tr["close"].mean()) / tr["close"].std(ddof=1)
    assert abs(nz.transform(va)["close"].iloc[0] - manual) < 1e-9
    h1 = nz.artifact_hash()
    p = pathlib.Path("freqtrade/user_data/rl_norm/_test_norm.json")
    nz.save(p)
    assert FitNormalizer.load(p).artifact_hash() == h1
    p.unlink()
    try:
        FitNormalizer(["close"]).transform(va)
        raise SystemExit("fit'siz transform yakalamalıydı")
    except ValueError:
        pass
    print("PASS 3 normalizer (train-fit, leakage-safe, roundtrip)")


def test_4_gates():
    base = {"trade_count": 10, "actions": {0: 90, 1: 5, 2: 5}, "invalid_actions": 0,
            "total_steps": 1000, "bankruptcy": False, "nan_reward": False,
            "obs_var": 1.5, "fees_paid": 1.0, "gross_profit": 5.0,
            "max_dd": -0.1, "timed_out": False, "exception": None, "n_days": 10}
    assert check_run(dict(base))["pass"] is True
    bad = dict(base, nan_reward=True, bankruptcy=True, timed_out=True,
               exception="x", invalid_actions=50, obs_var=0.0)
    r = check_run(bad)
    assert not r["pass"] and len(r["hard_fails"]) == 6, r
    w = check_run(dict(base, trade_count=0, actions={0: 100, 1: 0, 2: 0},
                       fees_paid=5.0, gross_profit=2.0, max_dd=None))
    assert w["pass"] is True  # warning'ler fail DEĞİL
    assert {"zero-trade", "only-HOLD", "fee > gross (fee ölümü)"} <= set(w["warnings"]), w
    w0 = check_run(dict(base, trade_count=5, max_dd=None))  # trade var ama DD yok
    assert "undefined MaxDD" in w0["warnings"]
    w2 = check_run(dict(base, actions={0: 50, 1: 50, 2: 0}))
    assert "BUY var + SELL yok (öğrenilmemiş çıkış)" in w2["warnings"]
    print("PASS 4 failure gates (6 hard-fail + warning sınıfları)")


def test_5_ent_coef_passthrough():
    from src.rl.train import build_model
    assert HyperparamConfig().ent_coef == 0.0
    env = TradingEnv(_synth(200), window=10)
    env.reset(seed=0)
    m = build_model("PPO", env, seed=0, n_steps=64, verbose=0, ent_coef=0.01)
    assert abs(float(m.ent_coef) - 0.01) < 1e-12
    print("PASS 5 ent_coef passthrough (shaping yok, parametre var)")


def test_6_diagnostics_callback():
    from stable_baselines3 import PPO
    from stable_baselines3.common.monitor import Monitor
    from src.rl.train import DiagnosticsCallback
    env = TradingEnv(_synth(400), window=10)
    env.reset(seed=0)
    menv = Monitor(env)
    m = PPO("MlpPolicy", menv, seed=0, verbose=0, n_steps=64)
    out = pathlib.Path("freqtrade/user_data/rl_norm/_test_diag.jsonl")
    if out.exists():
        out.unlink()
    m.learn(total_timesteps=256, callback=DiagnosticsCallback(str(out)))
    rows = out.read_text(encoding="utf-8").strip().split("\n")
    assert len(rows) >= 2, rows  # ≥2 rollout
    import json
    r0 = json.loads(rows[0])
    assert "actions" in r0 and "n_steps" in r0
    out.unlink()
    print(f"PASS 6 diagnostics callback ({len(rows)} rollout, aksiyon histogramlı)")


def test_7_timeout_callback():
    cb = wallclock_callback(-1)  # negatif limit -> ilk adımda patlar
    # (0 Windows tick granularitesinde patlamayabilir)
    try:
        cb._on_step()
        raise SystemExit("timeout yakalamalıydı")
    except TimeoutExceeded:
        pass
    print("PASS 7 wallclock timeout callback")


def test_8_thread_limits():
    from src.rl.determinism import apply_thread_limits, runtime_snapshot
    rep = apply_thread_limits(1)
    import torch
    assert torch.get_num_threads() == 1, torch.get_num_threads()
    assert rep["torch_threads"] == 1
    assert rep["cuda_available"] is False  # CPU-only politika
    snap = runtime_snapshot()
    assert snap["env_threads"]["OMP_NUM_THREADS"] == "1"
    print("PASS 8 thread limitleri (torch=1, CUDA yok)")


def test_9_canonical_hash():
    import json
    from src.rl.determinism import canonical_hash, save_artifacts
    a = [0, 1, 1, 0, 2] * 200
    e = [100.0 + i * 0.01 for i in range(1000)]
    r = [0.0] * 999 + [0.001]
    assert canonical_hash(a) == canonical_hash(list(a))
    assert canonical_hash(a) != canonical_hash(a[:-1] + [1])
    assert canonical_hash(e) == canonical_hash(list(e))
    p = pathlib.Path("freqtrade/user_data/rl_norm/_test_art.json")
    h = save_artifacts(p, a, e, r)
    back = json.loads(p.read_text(encoding="utf-8"))
    assert back["hashes"] == h and back["n_steps"] == 1000
    assert h["actions"] == canonical_hash(a) and h["equities"] == canonical_hash(e)
    assert h["rewards"] == canonical_hash(r)
    p.unlink()
    print("PASS 9 canonical hash + artifact roundtrip")


def test_10_seed_all_deterministic_mode():
    from src.rl.train import seed_all
    assert seed_all(5) == 5
    import torch
    assert torch.get_num_threads() == 1  # seed_all kilidi korur
    assert torch.are_deterministic_algorithms_enabled()
    print("PASS 10 seed_all thread+deterministik modu korur")


def test_12_grid47_caps():
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
    from scripts.phase47_tuning import GRID47, SEEDS, TIMESTEPS
    from src.rl.train import build_grid, load_experiment_config
    assert set(SEEDS) == {42, 7, 123, 2026, 999}
    assert len(GRID47) == 8 and TIMESTEPS == 600_000
    runs = build_grid({"algo": ["PPO"], "learning_rate": [1e-4, 3e-4],
                       "ent_coef": [0.0, 0.01], "n_steps": [2048, 4096]},
                      SEEDS, load_experiment_config())
    assert len(runs) == 8 * 5  # 8 config x 5 seed, cap 50/5 altı
    print("PASS 12 grid47 caps (8x5=40 runs, 50x5 altı)")


def test_11_model_hash_container_safe():
    from src.rl.train import build_model, seed_all
    from src.rl.determinism import hash_model_weights
    seed_all(11)
    m1 = build_model("PPO", TradingEnv(_synth(200), window=10), 11,
                     n_steps=64, verbose=0)
    seed_all(11)
    m2 = build_model("PPO", TradingEnv(_synth(200), window=10), 11,
                     n_steps=64, verbose=0)
    assert hash_model_weights(m1.get_parameters()) == \
        hash_model_weights(m2.get_parameters())
    seed_all(12)
    m3 = build_model("PPO", TradingEnv(_synth(200), window=10), 12,
                     n_steps=64, verbose=0)
    assert hash_model_weights(m1.get_parameters()) != \
        hash_model_weights(m3.get_parameters())
    print("PASS 11 model hash (container-safe, seed-duyarlı)")


if __name__ == "__main__":
    test_1_chunk_bounds()
    test_2_chunk_no_silent_drop()
    test_3_normalizer()
    test_4_gates()
    test_5_ent_coef_passthrough()
    test_6_diagnostics_callback()
    test_7_timeout_callback()
    test_8_thread_limits()
    test_9_canonical_hash()
    test_10_seed_all_deterministic_mode()
    test_11_model_hash_container_safe()
    test_12_grid47_caps()
    print("ALL PASS — 12/12 (training YOK; test 6 mini-learn içerir)")
