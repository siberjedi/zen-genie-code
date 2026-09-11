"""Phase 6A — feature formul + causality testleri (FINAL LOCK §6/§7/§9).

Sentetik veri uzerinde exact formul dogrulamasi; protected veri YUKLEMEZ.
Calistir: py -3 tests/test_phase6a_features.py
"""
import pathlib
import sys

TESTROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(TESTROOT))
sys.path.insert(0, str(TESTROOT / "scripts"))

import numpy as np
import pandas as pd

from phase6a_features import (build_features, causality_probe_xa,
                              rolling_mean_pairwise_corr, XA_COLS, UNIVERSE)

PASSED = []


def check(name, cond, detail=""):
    PASSED.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not cond:
        raise AssertionError(name)


print("== phase6a features ==")
probe_ok = True
try:
    causality_probe_xa()
except AssertionError:
    probe_ok = False
check("causality probe (shift(-) yok)", probe_ok)

# sentetik panel: 7 asset + BTC, deterministik
n = 600
t = np.arange(n)
grid = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=n, freq="5min", tz="UTC"),
                     "btc_close": 100.0 + t * 0.1})
closes = {}
for i, s in enumerate(UNIVERSE):
    closes[s] = 50.0 + (i + 1) * t * 0.05 + (i % 2) * 0.01 * t
f = build_features(grid, closes)
check("6 kolon", list(f.columns) == XA_COLS, f"{list(f.columns)}")
# tum getiriler pozitif -> breadth == 1 (warmup disi)
check("breadth_1 == 1 (pozitif trend)", (f["breadth_1"].dropna() == 1.0).all())
check("breadth_12 == 1 (pozitif trend)", (f["breadth_12"].dropna() == 1.0).all())
# dispersion: 1h returnlerin std'si (ddof=1) ile eslesmeli
r12 = np.column_stack([(closes[s][12:] / closes[s][:-12] - 1) for s in UNIVERSE])
check("dispersion formul", np.allclose(f["dispersion_12"].iloc[12:].to_numpy(),
                                       np.std(r12, axis=1, ddof=1), equal_nan=True))
# btc_rel: BTC 1h return - universe ort
rb = grid["btc_close"].to_numpy()[12:] / grid["btc_close"].to_numpy()[:-12] - 1
check("btc_rel formul", np.allclose(f["btc_rel_12"].iloc[12:].to_numpy(),
                                    rb - r12.mean(axis=1), equal_nan=True))
# eth/btc oran degisimi
ratio = closes["ETHUSDT"] / grid["btc_close"].to_numpy()
check("ethbtc formul", np.allclose(f["ethbtc_chg_12"].iloc[12:].to_numpy(),
                                   ratio[12:] / ratio[:-12] - 1, equal_nan=True))
# corr_regime: sabit oranli trendler -> korelasyon ~1
check("corr_regime ~1 (paralel trend)", (f["corr_regime"].dropna() > 0.99).all(),
      f"min={f['corr_regime'].min():.4f}")
check("corr warmup 288 NaN", f["corr_regime"].iloc[:288].isna().all()
      and f["corr_regime"].iloc[288:].notna().all())
# eksik bar -> satir NaN (drop politikasi); XRP'den bagimsiz ethbtc haric
closes2 = dict(closes)
arr = closes2["XRPUSDT"].copy()
arr[400:410] = np.nan
closes2["XRPUSDT"] = arr
f2 = build_features(grid, closes2)
dep_cols = ["breadth_1", "breadth_12", "dispersion_12", "btc_rel_12", "corr_regime"]
check("eksik bar NaN yayilimi", f2.loc[400:409, dep_cols].isna().all().all())
closes3 = dict(closes)
arr3 = closes3["ETHUSDT"].copy()
arr3[400:410] = np.nan
closes3["ETHUSDT"] = arr3
f3 = build_features(grid, closes3)
check("ETH eksik -> ethbtc NaN", f3.loc[400:409, ["ethbtc_chg_12"]].isna().all().all())
# rolling corr NaN penceresi
R = np.random.default_rng(0).normal(0, 1, (500, 7))
R[100, 3] = np.nan
c = rolling_mean_pairwise_corr(R, 288)
check("corr NaN pencere", np.isnan(c[100:388]).all() and not np.isnan(c[388]))

print()
fails = [n for n, c in PASSED if not c]
print(f"TOPLAM: {len(PASSED)} test, {len(fails)} hatali")
assert not fails, fails
print("ALL PASS")