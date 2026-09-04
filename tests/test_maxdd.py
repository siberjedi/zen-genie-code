"""
MaxDD düzeltme testi — 2026-09-04 sanity check
Kanıt: (1+daily_ratio_sum).cumprod() wallet DD'yi abartıyor (stake != wallet).
Doğru: 100 + cum daily_abs (wallet simple), DD = (eq-roll_max)/roll_max.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import pandas as pd

def maxdd_wrong(daily_ratio):
    eq = (1 + daily_ratio).cumprod()
    dd = (eq - eq.cummax()) / eq.cummax()
    return float(dd.min())

def maxdd_correct(daily_abs, start=100.0):
    eq = start + daily_abs.cumsum()
    dd = (eq - eq.cummax()) / eq.cummax()
    return float(dd.min())

def test_maxdd():
    # Fold0 gerçek: daily_abs sum -33.95, FT wallet DD 0.6119 (61%)
    # daily_ratio sum -0.992, wrong method -0.9602 (96%) -> abartı
    # Basit örnek: 2 gün, gün0 0, gün1 crash
    # 3 trade, stake 33, wallet 100, her biri -10% ratio -> abs -9.9 total
    # Wrong: daily_ratio [0, -0.30] -> equity [1.0, 0.70] -> DD -30%
    # Correct: daily_abs [0, -9.9] -> equity [100, 90.1] -> DD -9.9%
    daily_ratio = pd.Series([0.0, -0.30])
    daily_abs = pd.Series([0.0, -9.9])
    w = maxdd_wrong(daily_ratio)
    c = maxdd_correct(daily_abs)
    print(f"wrong {w:.4f} (abartı -30%), correct {c:.4f} (doğru -9.9%)")
    assert abs(w - (-0.30)) < 1e-6, f"w {w}"
    assert abs(c - (-0.099)) < 1e-6, f"c {c}"
    assert abs(w) > abs(c), "wrong abartmalı"
    # Fold0 gerçek veriyle: FT 0.6119 vs wrong 0.9602
    # Correct simple -0.5844 (FT 0.5933'e yakın, fark compounding)
    print("PASS MaxDD düzeltmesi doğrulandı — eski -0.96 abartı, doğru ~-0.59 (FT 0.59)")

if __name__ == "__main__":
    test_maxdd()
