"""Phase 6C — OI formul/alignment testleri (FINAL LOCK §6/§7/§8/§10).

Sentetik snapshot gridi uzerinde exact formul + asof kurali + dedup semanti.
Protected veri YUKLEMEZ. Calistir: py -3 tests/test_phase6c_features.py
"""
import pathlib
import sys

TESTROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(TESTROOT))
sys.path.insert(0, str(TESTROOT / "scripts"))

import numpy as np
import pandas as pd

from phase6c_features import build_features, causality_probe_oc, OI_COLS

PASSED = []


def check(name, cond, detail=""):
    PASSED.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not cond:
        raise AssertionError(name)


print("== phase6c features ==")
probe_ok = True
try:
    causality_probe_oc()
except AssertionError:
    probe_ok = False
check("causality probe", probe_ok)

n = 600
oi = 1000.0 + np.arange(n) * 0.5  # monoton artan
bc = 100.0 + np.arange(n) * 0.1
f = build_features(oi, bc)
check("5 kolon", list(f.columns) == OI_COLS)
check("chg_12 formul", np.allclose(f["oi_chg_12"].iloc[12:].to_numpy(),
                                   oi[12:] / oi[:-12] - 1))
check("chg_1 formul", np.allclose(f["oi_chg_1"].iloc[1:].to_numpy(),
                                  oi[1:] / oi[:-1] - 1))
s = pd.Series(oi)
mu = s.rolling(288, min_periods=288).mean().to_numpy()
sd = s.rolling(288, min_periods=288).std(ddof=1).to_numpy()
check("z_288 formul", np.allclose(f["oi_z_288"].iloc[287:].to_numpy(),
                                  (oi[287:] - mu[287:]) / sd[287:])
      and f["oi_z_288"].iloc[:287].isna().all())
rb = bc[12:] / bc[:-12] - 1
check("price_div (+/+ -> +1)", (f["oi_price_div"].iloc[12:].dropna() == 1.0).all())
mn = s.rolling(288, min_periods=288).min().to_numpy()
mx = s.rolling(288, min_periods=288).max().to_numpy()
check("range_288 formul", np.allclose(f["oi_range_288"].iloc[287:].to_numpy(),
                                      (oi[287:] - mn[287:]) / (mx[287:] - mn[287:])))
check("range [0,1]", ((f["oi_range_288"].dropna() >= 0)
                       & (f["oi_range_288"].dropna() <= 1)).all())
# flat gun -> 0.5 (kilitli)
oi_flat = np.full(n, 500.0)
ff = build_features(oi_flat, bc)
check("flat range 0.5", (ff["oi_range_288"].iloc[288:] == 0.5).all())
check("flat z NaN (sd=0)", ff["oi_z_288"].iloc[288:].isna().all())
# eksik snapshot -> NaN yayilimi
oi2 = oi.copy()
oi2[400:410] = np.nan
f2 = build_features(oi2, bc)
check("eksik snapshot NaN", f2.loc[400:409, ["oi_chg_12", "oi_z_288", "oi_chg_1"]].isna().all().all())

print()
fails = [n for n, c in PASSED if not c]
print(f"TOPLAM: {len(PASSED)} test, {len(fails)} hatali")
assert not fails, fails
print("ALL PASS")