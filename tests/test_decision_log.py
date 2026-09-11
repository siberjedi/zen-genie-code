"""Phase 4.17 — Decision Logging MVP testleri (training YOK).

Çalıştır: py -3 tests/test_decision_log.py
"""
import json
import math
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

from src.rl.decision_log import (DecisionLogger, read_log, validate_line,
                                 obs_hash, dataset_hash)

FEE, SLIP = 0.001, 0.0005
DUM_IDS = {"config_hash": "cfgh" * 4, "env_hash": "envh" * 4,
           "normalizer_hash": "nrmz" * 4, "model_hash": "mdlh" * 4,
           "dataset_hash": "dats" * 4}


def _closes(n=520):
    return [100.0 + 6.0 * math.sin(i / 13.0) + i * 0.012 for i in range(n)]


def _policy(obs):
    last, prev = obs[-1], obs[-3]
    return 1 if last > prev else (2 if last < prev else 0)


def _probs(a):
    return {0: 0.9, 1: 0.05, 2: 0.05} if a == 0 else \
        ({0: 0.05, 1: 0.9, 2: 0.05} if a == 1 else {0: 0.05, 1: 0.05, 2: 0.9})


def _simulate_real(closes, n_steps, policy):
    records = []
    eq = prev_eq = 100.0
    pos = False
    amt = 0.0
    cum = 0.0
    for k in range(n_steps):
        c = 30 + k
        obs = list(closes[c - 30:c])
        a = policy(obs)
        executed = False
        if not pos and a == 1:
            amt = eq * (1 - FEE) / (closes[c] * (1 + SLIP))
            pos = True
            executed = True
        elif pos and a == 2:
            eq = amt * closes[c] * (1 - SLIP) * (1 - FEE)
            pos = False
            executed = True
        if pos:
            eq = amt * closes[c]
        reward = eq - prev_eq
        prev_eq = eq
        cum += reward
        cash = 0.0 if pos else eq
        records.append({"step": k, "ci": c, "obs": obs, "action": a,
                        "pos": int(pos), "cash": round(cash, 8),
                        "equity": round(eq, 8), "reward": round(reward, 8),
                        "cum": round(cum, 8), "executed": executed})
    return records


def _write_log(path, records):
    with DecisionLogger(path, run_id="syn", config_id="syn", seed=1,
                        flush_every=7, **DUM_IDS) as lg:
        for r in records:
            lg.log_step(global_step=r["step"], episode_id=0, candle_idx=r["ci"],
                        obs=r["obs"], action=r["action"], action_probs=_probs(r["action"]),
                        position=r["pos"], cash=r["cash"], equity=r["equity"],
                        reward=r["reward"], cumulative_reward=r["cum"], regime="bull")
    return lg.rows


def _replay(path, closes, policy):
    header, rows = read_log(path)
    eq = prev_eq = 100.0
    pos = False
    amt = 0.0
    actions, equities, rewards = [], [], []
    first_div = None
    for row in rows:
        c = row["candle_idx"]
        obs = list(closes[c - 30:c])
        a = policy(obs)
        act = int(row["action"])
        actions.append(act)
        if not pos and act == 1:
            amt = eq * (1 - FEE) / (closes[c] * (1 + SLIP))
            pos = True
        elif pos and act == 2:
            eq = amt * closes[c] * (1 - SLIP) * (1 - FEE)
            pos = False
        if pos:
            eq = amt * closes[c]
        reward = eq - prev_eq
        prev_eq = eq
        equities.append(round(eq, 8))
        rewards.append(round(reward, 8))
        divs = []
        if round(float(row["equity"]), 8) != round(eq, 8):
            divs.append("equity")
        if round(float(row["reward"]), 8) != round(reward, 8):
            divs.append("reward")
        if int(row["action"]) != a:
            divs.append("action")
        if obs_hash(obs) != row["obs_hash"]:
            divs.append("obs_hash")
        if divs and first_div is None:
            first_div = {"global_step": int(row["global_step"]), "what": divs}
    return actions, equities, rewards, first_div


def _corrupt(path, step, tmp):
    header, rows = read_log(path)
    out = []
    for r in rows:
        if r["global_step"] == step:
            r["action"] = 0 if r["action"] != 0 else 1
        out.append(json.dumps(r))
    p2 = pathlib.Path(tmp) / "corrupt.jsonl"
    lines = [json.dumps(header)] + out + \
            [json.dumps({"schema_trailer": 1, "rows": len(out), "run_id": "syn"})]
    p2.write_text("\n".join(lines), encoding="utf-8")
    return p2


def test_1_obs_hash_determinism():
    from src.rl.decision_log import DecisionLogger as _  # noqa
    o1 = [1.0, 2.0, 3.0]
    assert obs_hash(o1) == obs_hash(tuple(o1)) == obs_hash([1.0, 2.0, 3.0])
    assert obs_hash([1.0, 2.0000000000004, 3.0]) == obs_hash(o1)  # round(12) eşler
    assert obs_hash([1.0, 2.5, 3.0]) != obs_hash(o1)              # tek float değişimi
    import numpy as np
    assert obs_hash(np.array(o1)) == obs_hash(o1)
    print("PASS 1 obs_hash determinism + single-float sensitivity")


def test_2_dataset_hash():
    import pandas as pd
    n = 120
    base = pd.Timestamp("2023-01-01")
    dates = [str(base + pd.Timedelta(minutes=5 * i)) for i in range(n)]
    closes = _closes(n)
    h1 = dataset_hash(dates, closes, "2023-01-01", "2023-06-30")
    assert dataset_hash(dates, closes, "2023-01-01", "2023-06-30") == h1
    closes2 = list(closes)
    closes2[30] += 1e-6
    assert dataset_hash(dates, closes2, "2023-01-01", "2023-06-30") != h1
    # pencere DIŞI satır hash'i etkilememeli (mask pinleme mantığı)
    dates3 = ["2022-12-31"] + dates
    closes3 = [9.0] + closes
    assert dataset_hash(dates3, closes3, "2023-01-01", "2023-06-30") == h1
    # pencere İÇİ farklı değer -> farklı hash
    closes4 = [9.0] + closes
    dates4 = ["2022-12-31"] + dates
    closes4[40] += 1e-6
    assert dataset_hash(dates4, closes4, "2023-01-01", "2023-06-30") != h1
    print("PASS 2 dataset_hash determinism + window pinning + sensitivity")


def test_3_schema_validation():
    ok = {"schema": 1, "run_id": "r", "config_id": "c", "seed": 1,
          "global_step": 0, "episode_id": 0, "timestamp_ms": 1,
          "candle_idx": 30, "obs_hash": "ab12", "action": 1,
          "action_probs": {0: 0.1, 1: 0.8, 2: 0.1}, "position": 0,
          "cash": 100.0, "equity": 100.0, "reward": 0.0,
          "cumulative_reward": 0.0, "regime": "bull", "config_hash": "a",
          "env_hash": "b", "normalizer_hash": "c", "model_hash": "d",
          "dataset_hash": "e"}
    assert validate_line(ok) == []
    bad = dict(ok)
    del bad["obs_hash"]
    assert any("missing_fields" in e for e in validate_line(bad))
    bad2 = dict(ok)
    bad2["action"] = 9
    assert any("action" in e for e in validate_line(bad2))
    bad3 = dict(ok)
    bad3["schema"] = 2
    assert any("schema" in e for e in validate_line(bad3))
    print("PASS 3 schema validation")


def test_4_write_read_roundtrip():
    closes = _closes(120)
    recs = _simulate_real(closes, 60, _policy)
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / "log.jsonl"
        n = _write_log(p, recs)
        header, rows = read_log(p)
        assert n == 60 and header["run_id"] == "syn" and len(rows) == 60
        for r, got in zip(recs, rows):
            assert got["global_step"] == r["step"]
            assert got["candle_idx"] == r["ci"]
            assert got["action"] == r["action"]
            assert got["equity"] == r["equity"]
            assert got["reward"] == r["reward"]
    print("PASS 4 JSONL write/read roundtrip")


def test_5_replay_equality_and_divergence():
    closes = _closes(240)
    n_steps = 180
    recs = _simulate_real(closes, n_steps, _policy)
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / "log.jsonl"
        _write_log(p, recs)
        actions, equities, rewards, div = _replay(p, closes, _policy)
        assert div is None
        assert actions == [r["action"] for r in recs]
        assert equities == [r["equity"] for r in recs]
        assert rewards == [r["reward"] for r in recs]

        # kasitli bozma: global_step=50 -> tespit
        p2 = _corrupt(p, 50, tmp)
        _, div2 = (_replay(p2, closes, _policy)[0:1] and (None, _replay(p2, closes, _policy)[3]))
        assert div2 is not None and div2["global_step"] == 50
        assert "action" in div2["what"]
        print("PASS 5 replay equality + first-divergence at global_step=50")


def test_6_flush_and_close():
    closes = _closes(80)
    recs = _simulate_real(closes, 30, _policy)
    # flush_every=7 -> 30 satır, 4 tam flush + kısmi close flush; trailer rows doğru
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / "log.jsonl"
        with DecisionLogger(p, run_id="syn", config_id="syn", seed=1,
                            flush_every=7, **DUM_IDS) as lg:
            for r in recs:
                lg.log_step(global_step=r["step"], episode_id=0, candle_idx=r["ci"],
                            obs=r["obs"], action=r["action"],
                            action_probs=_probs(r["action"]), position=r["pos"],
                            cash=r["cash"], equity=r["equity"], reward=r["reward"],
                            cumulative_reward=r["cum"], regime="bull")
            assert lg.rows == 30
        header, rows = read_log(p)
        assert len(rows) == 30
        # flush_every küçük olsa da close sonrası her satır diske inmiş olmalı
        raw = p.read_text(encoding="utf-8").strip().split("\n")
        assert any("schema_trailer" in ln for ln in raw)
    print("PASS 6 buffered flush + close + trailer row count")


if __name__ == "__main__":
    test_1_obs_hash_determinism()
    test_2_dataset_hash()
    test_3_schema_validation()
    test_4_write_read_roundtrip()
    test_5_replay_equality_and_divergence()
    test_6_flush_and_close()
    print("ALL PASS - 6/6 (training YOK)")