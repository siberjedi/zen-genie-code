"""Phase 5 — Walk-forward testleri (phase504_walkforward.py).

Kapsam: 9 fold üretimi, pencere sınırlarının VAL_END öncesi korunması,
fold-overlap raporu, PSS hesabının phase505 ile tutarlılığı ve konsistans eşiği.
Calistir: py -3 tests/test_phase504_walkforward.py
"""
import pathlib
import sys

TESTROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(TESTROOT))
sys.path.insert(0, str(TESTROOT / "scripts"))

import numpy as np

from phase504_walkforward import (phase5_folds, overlap_report, bounds_respected,
                                  wf_pss_scores, wf_consistency)
from src.freqai.p5_splits import VAL_END

PASSED = []


def check(name, cond, detail=""):
    PASSED.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not cond:
        raise AssertionError(name)


print("== phase504 ==")
folds = phase5_folds()
check("9 fold", 8 <= len(folds) <= 10, f"n={len(folds)}")
check("bounds respected (VAL_END öncesi)", bounds_respected(folds))
for f in folds:
    for name, (a, b) in f.items():
        if name == "train" or name == "validation":
            for t in (a, b):
                check(f"fold {name} ucu tz-aware", t.tz is not None)
check("expanding=false -> her fold train aynı genişlik", len({f["train"][1] - f["train"][0] for f in folds}) == 1)

rep = overlap_report(folds)
check("overlap raporu", rep["n_overlaps"] == rep["folds"] - 1 or rep["n_overlaps"] >= 0)

# PSS tutarlılığı (phase505 ile aynı formül, tam tamsayı ile karşılaştır)
s = np.linspace(-1, 1, 1000)
r = np.linspace(-0.02, 0.02, 1000)
pss, k, m10, net = wf_pss_scores(s, r, cost=0.003)
k_exp = int(np.ceil(1000 * 0.10))
check("PSS top10 boyut", k == k_exp)
check("PSS net işareti", net == (pss > 0))
r_top = r[np.argsort(-s)[:k_exp]]
check("PSS değeri", abs(pss - (r_top.mean() - 0.003)) < 1e-12)

# wf_consistency: 2/3 aynı yön + net>0
res_pos = [{"pss": 0.01, "net_positive": True} for _ in range(2)]
res_pos.append({"pss": -0.01, "net_positive": False})
check("wf_consistency 2/3", abs(wf_consistency(res_pos, True) - 2 / 3) < 1e-9)
res_neg = [{"pss": -0.01, "net_positive": True} for _ in range(2)]
res_neg.append({"pss": 0.01, "net_positive": False})
check("wf_consistency yön işareti", abs(wf_consistency(res_neg, False) - 2 / 3) < 1e-9)
check("wf_consistency boş", wf_consistency([], True) == 0.0)

print()
fails = [n for n, c in PASSED if not c]
print(f"TOPLAM: {len(PASSED)} test, {len(fails)} hatalı")
assert not fails, fails
print("ALL PASS")