"""Phase 6B — funding formul/settlement testleri (FINAL LOCK §6/§7/§8/§9).

Sentetik settlement gridi uzerinde exact formul + availability kurali.
Protected veri YUKLEMEZ. Calistir: py -3 tests/test_phase6b_features.py
"""
import pathlib
import sys

TESTROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(TESTROOT))
sys.path.insert(0, str(TESTROOT / "scripts"))

import numpy as np
import pandas as pd

from phase6b_features import (build_features, settlement_features,
                              causality_probe_fb, FUND_COLS)

PASSED = []


def check(name, cond, detail=""):
    PASSED.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not cond:
        raise AssertionError(name)


print("== phase6b features ==")
probe_ok = True
try:
    causality_probe_fb()
except AssertionError:
    probe_ok = False
check("causality+predicted exclusion probe", probe_ok)

# sentetik: 40 settlement (8h), degerler deterministik
m = 40
T0 = int(pd.Timestamp("2020-01-01", tz="UTC").timestamp() * 1000)
STEP = 8 * 3600 * 1000
fms = np.array([T0 + j * STEP for j in range(m)], dtype="int64")
rates = np.array([0.0001 * ((j % 5) - 2) for j in range(m)], float)
sf = settlement_features(rates)
check("5 kolon", sorted(sf.keys()) == sorted(FUND_COLS))
check("F1 = ham oran", np.allclose(sf["fund_rate"], rates))
mu30 = pd.Series(rates).rolling(30, min_periods=30).mean().to_numpy()
sd30 = pd.Series(rates).rolling(30, min_periods=30).std(ddof=1).to_numpy()
check("F2 z-formul", np.allclose(sf["fund_z_30"][29:], (rates[29:] - mu30[29:]) / sd30[29:])
      and np.isnan(sf["fund_z_30"][:29]).all())
check("F3 sign", (sf["fund_sign"] == np.sign(rates)).all())
check("F4 abs-chg", np.allclose(sf["fund_abs_chg"][1:], np.abs(np.diff(rates)))
      and np.isnan(sf["fund_abs_chg"][0]))
# persist: rates pattern [-2,-1,0,1,2]/1e4 per 5 -> sign: -,-,0,+,+,-,-,0,+,+,...
exp_persist = []
run, prev = 0, 0.0
for v in rates:
    s = float(np.sign(v))
    if s == 0.0:
        run, prev = 0, 0.0
        exp_persist.append(0.0)
    elif s == prev:
        run = min(run + 1, 8)
        exp_persist.append(float(run))
    else:
        run, prev = 1, s
        exp_persist.append(1.0)
check("F5 persist+cap+sifir-reset", (sf["fund_persist"] == np.array(exp_persist)).all())
check("F5 cap<=8", (sf["fund_persist"] <= 8).all())

# availability kurali: T anindaki candle R(T)'yi gorur, onceki gormez
H = 5 * 60 * 1000
grid = np.arange(T0 - 2 * H, T0 + 2 * STEP + H, H)  # T0 oncesi + 2 gun
f = build_features(grid, fms, rates)
i_T0 = int(np.where(grid == T0)[0][0])
check("settlement candle yeni orani gorur",
      f["fund_rate"].iloc[i_T0] == rates[0], f"got={f['fund_rate'].iloc[i_T0]}")
check("onceki candle eski orani gorur (yoksa NaN)",
      np.isnan(f["fund_rate"].iloc[i_T0 - 1]))
i_T1 = int(np.where(grid == T0 + STEP)[0][0])
check("sonraki settlement gunceller", f["fund_rate"].iloc[i_T1] == rates[1])
# merdiven sabitligi: iki settlement arasi deger sabit
mid = f["fund_rate"].iloc[i_T0 + 1:i_T1].to_numpy()
check("aralikta sabit (ffill merdiven)", (mid == rates[0]).all())

print()
fails = [n for n, c in PASSED if not c]
print(f"TOPLAM: {len(PASSED)} test, {len(fails)} hatali")
assert not fails, fails
print("ALL PASS")