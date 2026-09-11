"""Convention guards (cp1254-safe: this file is ASCII-only by design).

T1: to_ms unit invariance (+ parity with the locked legacy expression).
T2: timezone guard (naive->UTC, aware unchanged, non-UTC instant preserved).
T3: no NEW fragile direct datetime-to-int64 sites in
    scripts/+src/+tests beyond the locked per-file map below.
    Two-step same-dtype comparisons are reviewer responsibility (out of scope).
    Migrating a site requires updating EXPECTED_FRAGILE in the same change.
T4: no NEW non-ASCII string literals in tests/*.py beyond the locked map.
Run: py -m pytest tests/test_conventions.py -q
"""
import ast
import pathlib
import sys

import pandas as pd

TESTROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTROOT))

from src.timeconv import ensure_utc, to_ms

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")

# Locked 2026-09-10: direct fragile-pattern counts per file.
# Phase 9D: phase6a_run/6b_run/6c_run sites migrated to src.timeconv.to_ms (0 remain).
# Phase 9E: phase7_run site migrated to src.timeconv.to_ms (0 remain).
# Phase 9F: phase8_m20_reeval site migrated to src.timeconv.to_ms (0 remain).
# Guard aktif: yeni bir fragile site eklenirse found != {} -> FAIL.
EXPECTED_FRAGILE = {}

# Locked 2026-09-10: non-ASCII string-literal counts per test file.
EXPECTED_NONASCII = {
    "tests/test_capital_protection.py": 0,
    "tests/test_conventions.py": 0,
    "tests/test_decision_log.py": 1,
    "tests/test_freqai_readiness.py": 3,
    "tests/test_holdout_registry.py": 5,
    "tests/test_maxdd.py": 5,
    "tests/test_phase418.py": 1,
    "tests/test_phase500.py": 8,
    "tests/test_phase501_features.py": 7,
    "tests/test_phase502_labels.py": 7,
    "tests/test_phase503_models.py": 6,
    "tests/test_phase504_walkforward.py": 8,
    "tests/test_phase505_stats.py": 7,
    "tests/test_phase6a_features.py": 1,
    "tests/test_phase6b_features.py": 1,
    "tests/test_phase6c_features.py": 1,
    "tests/test_power.py": 1,
    "tests/test_rl_hardened.py": 14,
    "tests/test_rl_mask.py": 5,
    "tests/test_rl_phase44.py": 12,
    "tests/test_rl_phase49.py": 7,
    "tests/test_rl_reward_modes.py": 5,
    "tests/test_sharpe_annualization.py": 3,
}

KNOWN_INSTANT_MS = 1577836800000  # 2020-01-01 00:00 UTC


def _fragile_count(text):
    return sum(1 for line in text.splitlines()
               if "pd.to_datetime(" in line and ".astype(" in line
               and "int64" in line)


def test_t1_unit_invariance():
    base = pd.Timestamp("2023-06-15 12:34:56", tz="UTC")
    s_ns = pd.Series(pd.to_datetime(["2020-01-01 00:00:00", "2023-06-15 12:34:56"],
                                      utc=True))
    s_ms = s_ns.astype("datetime64[ms, UTC]")
    s_s = s_ns.astype("datetime64[s, UTC]")
    assert (to_ms(s_ns) == to_ms(s_ms)).all()
    assert (to_ms(s_ns) == to_ms(s_s)).all()
    assert int(to_ms(s_ns)[0]) == KNOWN_INSTANT_MS
    assert to_ms(base) == int((base - EPOCH) // pd.Timedelta("1ms"))
    assert to_ms(pd.DatetimeIndex(s_ns)) .tolist() == to_ms(s_ns).tolist()
    assert to_ms("2020-01-01") == KNOWN_INSTANT_MS
    # parity with the locked legacy expression (phase10/phase11 copies)
    t = pd.to_datetime(s_ns)
    if getattr(t.dt, "tz", None) is None:
        t = t.dt.tz_localize("UTC")
    legacy = ((t - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta("1ms")).to_numpy()
    assert (to_ms(s_ns) == legacy).all()
    assert to_ms(s_ns).dtype == "int64"


def test_t2_timezone_guard():
    naive = pd.Series(pd.to_datetime(["2020-01-01", "2023-01-01"]))
    out = ensure_utc(naive)
    assert str(out.dt.tz) == "UTC"
    assert (to_ms(naive) == to_ms(out)).all()
    aware = pd.Series(pd.to_datetime(["2020-01-01"], utc=True))
    assert ensure_utc(aware).equals(aware)
    other = pd.Series([pd.Timestamp("2020-01-01 03:00", tz="Europe/Istanbul")])
    conv = ensure_utc(other)
    assert str(conv.dt.tz) == "UTC"
    assert conv.iloc[0] == other.iloc[0]  # same instant
    assert to_ms(other)[0] == to_ms(conv)[0]
    assert ensure_utc(pd.Timestamp("2020-01-01", tz="UTC")) == pd.Timestamp("2020-01-01", tz="UTC")
    assert ensure_utc(pd.Timestamp("2020-01-01")) == pd.Timestamp("2020-01-01", tz="UTC")
    try:
        pd.Series(pd.to_datetime(["2020-01-01"], utc=True)).dt.tz_localize("UTC")
        raised = False
    except TypeError:
        raised = True
    assert raised  # documents why the bare pattern is fragile


def test_t3_no_new_fragile_astype():
    found = {}
    for d in ("scripts", "src", "tests"):
        for f in sorted((TESTROOT / d).rglob("*.py")):
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            n = _fragile_count(text)
            if n:
                found[f.relative_to(TESTROOT).as_posix()] = n
    assert found == EXPECTED_FRAGILE, f"fragile-site map changed: {found}"


def test_t4_no_new_nonascii_literals():
    found = {}
    for f in sorted((TESTROOT / "tests").glob("test_*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        n = sum(1 for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
                and any(ord(c) > 127 for c in node.value))
        found[f.name if f.name != "test_conventions.py" else "tests/test_conventions.py"] = n
    norm = {("tests/" + k if not k.startswith("tests/") else k): v
            for k, v in found.items()}
    assert norm == EXPECTED_NONASCII, f"non-ascii map changed: {norm}"
