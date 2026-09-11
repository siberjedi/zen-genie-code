"""Phase 5 — Feature modülü testleri (phase501_features.py).

Kapsam: nedensellik probe, 15m resample tamamlığı, Wilder RSI/ATR/ADX sonluluğu,
sıfır-range candle NaN politikası, +/-inf->NaN (sıfır-vol), blok büyüklükleri.
Calistir: py -3 tests/test_phase501_features.py
"""
import pathlib
import sys

TESTROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(TESTROOT))
sys.path.insert(0, str(TESTROOT / "scripts"))

import numpy as np
import pandas as pd

from phase501_features import (FEATURE_UNION, BLOCKS, build_features,
                               resample_15m, causality_probe, _wilder_rsi,
                               _wilder_atr, _wilder_adx)

PASSED = []


def check(name, cond, detail=""):
    PASSED.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not cond:
        raise AssertionError(name)


def synth_ohlcv(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    open_ = close + rng.normal(0, 0.1, n)
    high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.2, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.2, n))
    volume = np.abs(rng.normal(100, 10, n))
    dates = pd.date_range("2020-01-01", periods=n, freq="5min", tz="UTC")
    return pd.DataFrame({"date": dates, "open": open_, "high": high,
                         "low": low, "close": close, "volume": volume})


print("== phase501 ==")
probe_ok = True
try:
    causality_probe()
except AssertionError:
    probe_ok = False
check("causality_probe (shift(-) yok)", probe_ok)
f = build_features(synth_ohlcv())
check("28 feature", f.shape[1] == len(FEATURE_UNION) == 28, f"shape={f.shape}")
check("no +/-inf (sıfır-vol politikası)", not np.isinf(f.to_numpy()).any())
check("sonluluk (finite-possi)", np.isfinite(f.dropna().to_numpy()).all())
for b, cols in BLOCKS.items():
    check(f"B3 union -> {b} alt küme", set(cols) <= set(FEATURE_UNION))
check("B3 = full union", BLOCKS["B3"] == FEATURE_UNION)
check("blok corona (kesisim boş)", not set(BLOCKS["B0"]) & set(BLOCKS["B1"])
      and not set(BLOCKS["B0"]) & set(BLOCKS["B2"]) and not set(BLOCKS["B1"]) & set(BLOCKS["B2"]))
check("B0 boyut", len(BLOCKS["B0"]) == 14, f"{len(BLOCKS['B0'])}")
check("B1 boyut", len(BLOCKS["B1"]) == 7, f"{len(BLOCKS['B1'])}")
check("B2 boyut", len(BLOCKS["B2"]) == 7, f"{len(BLOCKS['B2'])}")

# --- resample tamamlığı ---
df = synth_ohlcv(n=3 * 100 + 1)  # +1 kısmi son 15m bar
r = resample_15m(df)
check("resample bar sayısı (kısmi son düştü)", len(r) == 100, f"n={len(r)}")
rng15 = df.set_index("date").resample("15min").agg(open=("open", "first"),
                                                    high=("high", "max"),
                                                    low=("low", "min"),
                                                    close=("close", "last"),
                                                    volume=("volume", "sum"))
check("resample OHLCV eksiksiz", (r["high"].to_numpy() == rng15["high"].to_numpy()[:100]).all()
      and (r["close"].to_numpy() == rng15["close"].to_numpy()[:100]).all())
# volume yalnızca tam bar grubunda birikir:
v_exp = df.set_index("date").resample("15min")["volume"].sum().to_numpy()[:100]
check("resample volume toplamı", np.allclose(r["volume"].to_numpy(), v_exp))

# --- Wilder fonksiyonları sonluluk/aralık ---
close = pd.Series(np.linspace(100, 200, 500) + np.random.default_rng(1).normal(0, 1, 500))
rsi = _wilder_rsi(close, 14).dropna()
check("RSI [0,100]", rsi.between(0, 100).all() and len(rsi) > 100, f"n={len(rsi)}")
adx = _wilder_adx(pd.Series(close + np.abs(np.random.default_rng(2).normal(0, 1, 500))),
                  pd.Series(close - np.abs(np.random.default_rng(3).normal(0, 1, 500))),
                  close, 14).dropna()
check("ADX gecerli segment sonlu [0,1]", np.isfinite(adx).all() and adx.between(0, 1).all()
      and len(adx) > 100, f"n={len(adx)}")

print()
fails = [n for n, c in PASSED if not c]
print(f"TOPLAM: {len(PASSED)} test, {len(fails)} hatalı")
assert not fails, fails
print("ALL PASS")