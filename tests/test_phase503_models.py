"""Phase 5 — Model fabrikaları testleri (phase503_models.py).

Kapsam: deterministik cell_seed, üç model (M1 LR-scaler, M2 RF, M3 LGBM) +
baseline, fit_predict determinizmi, scaler train-only (val'e uygulanır), finitlik.
Calistir: py -3 tests/test_phase503_models.py
"""
import pathlib
import sys

TESTROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(TESTROOT))
sys.path.insert(0, str(TESTROOT / "scripts"))

import numpy as np

from phase503_models import (M1, M2, M3, BASE, make_model, fit_predict,
                             fit_baseline_scores, cell_seed)

PASSED = []


def check(name, cond, detail=""):
    PASSED.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not cond:
        raise AssertionError(name)


rng = np.random.default_rng(42)
X = rng.normal(0, 1, (500, 7))
Xv = rng.normal(0, 1, (200, 7))
y_cls = (rng.random(500) > 0.7).astype(float)
y_reg = rng.normal(0, 0.1, 500)

print("== phase503 ==")
check("cell_seed deterministik", cell_seed("E001", 42) == cell_seed("E001", 42))
check("cell_seed hücre/seed'e duyarlı", cell_seed("E001", 42) != cell_seed("E002", 42)
      and cell_seed("E001", 42) != cell_seed("E001", 7))

for lb, yt, yv in (("L1", y_cls, (rng.random(200) > 0.7).astype(float)),
                   ("L2", y_reg, rng.normal(0, 0.1, 200))):
    for md in (M1, M2, M3):
        est, scaler = make_model(md, lb, 42)
        s1, _, sc1 = fit_predict(est, scaler, X, yt, Xv)
        est2, scaler2 = make_model(md, lb, 42)
        s2, _, sc2 = fit_predict(est2, scaler2, X, yt, Xv)
        check(f"{md} {lb} deterministik", np.allclose(s1, s2))
        check(f"{md} {lb} finit", np.isfinite(s1).all(), f"nan={np.isnan(s1).sum()}")
        if lb == "L1":
            check(f"{md} L1 proba [0,1]", (s1 >= 0).all() and (s1 <= 1).all(),
                  f"mean={s1.mean():.3f}")

# scaler train-only: M1 scaler'ı val'e uygulanır, fit transform edilmez
est, scaler = make_model(M1, "L1", 42)
_ = scaler.fit_transform(X)
sc_mean = scaler.mean_.copy()
_ = fit_predict(est, scaler, X, y_cls, Xv)
check("scaler train-only (transform uygulanır)", np.allclose(scaler.mean_, sc_mean))

# baseline
bs_pr, meta = fit_baseline_scores(y_cls, np.ones(50), "L1", 42)
check("BASE L1 puan = train baz oranı", np.allclose(bs_pr, np.clip(y_cls.mean(), 1e-9, 1 - 1e-9)))
bs_r, _ = fit_baseline_scores(y_reg, np.ones(50), "L2", 42)
check("BASE L2 puan = train ortalaması", np.allclose(bs_r, np.mean(y_reg)))

print()
fails = [n for n, c in PASSED if not c]
print(f"TOPLAM: {len(PASSED)} test, {len(fails)} hatalı")
assert not fails, fails
print("ALL PASS")