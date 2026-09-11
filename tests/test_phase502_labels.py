"""Phase 5 — Labels/split testleri (phase502_labels.py).

Kapsam: loader pencere koruması (FINAL korunur), Y off-by-one (base mum içermez),
label-bound kuralı, split eğitim/val ayrımı + lookahead yok, korumalar tetiklenir.
Calistir: py -3 tests/test_phase502_labels.py
"""
import pathlib
import sys

TESTROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(TESTROOT))
sys.path.insert(0, str(TESTROOT / "scripts"))

import numpy as np
import pandas as pd

from phase502_labels import (label_bound_mask, compute_labels, expected_dropped,
                             COST_C, H_PRIMARY, H_SECONDARY_15M, LABELS, TF_MINUTES)

from src.freqai.p5_splits import (TRAIN_START, TRAIN_END, VAL_START, VAL_END,
                                  FINAL_A_START, FINAL_B_START, FINAL_C_START,
                                  FINAL_P5_START)

PASSED = []


def check(name, cond, detail=""):
    PASSED.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not cond:
        raise AssertionError(name)


print("== phase502 ==")
df = pd.DataFrame({
    "date": pd.date_range("2020-01-01", periods=60, freq="5min", tz="UTC"),
    "open": 100.0, "high": 101.0, "low": 99.0,
    "close": [100 + i for i in range(60)], "volume": 100.0,
})
labs = compute_labels(df, horizon=H_PRIMARY)
# 1) off-by-one: Y(t) = close[t+12]/close[t] - 1 ; base mum icermez
check("Y horizon=12 (base mum yok)",
      np.allclose(labs["future_return"].iloc[:48].to_numpy(),
                  (np.arange(100 + 12, 100 + 60) / np.arange(100, 100 + 48)) - 1))
check("son H satır NaN", labs["future_return"].iloc[-H_PRIMARY:].isna().all())
check("L0 = Y>0 (NaN satırlar hariç)",
      (labs["L0"][labs["future_return"].notna()]
       == (labs["future_return"][labs["future_return"].notna()] > 0)).all())
check("L0 NaN = future NaN", (labs["L0"].isna() == labs["future_return"].isna()).all())
check("L1 = Y>C ile C=0.003",
      (labs["L1"][labs["future_return"].notna()]
       == (labs["future_return"][labs["future_return"].notna()] > COST_C)).all())
check("L2 = Y", np.isclose(labs["L2"], labs["future_return"], equal_nan=True).all())

# 2) label-bound kuralı: pencere end - H*tf
ts = pd.to_datetime(df["date"]).as_unit("ns") if hasattr(pd.to_datetime(df["date"]), "as_unit") else pd.to_datetime(df["date"])
m = label_bound_mask(ts, "2020-01-01", "2020-01-01 03:00", H_PRIMARY, TF_MINUTES)
cutoff = pd.Timestamp("2020-01-01 03:00", tz="UTC") - pd.Timedelta(minutes=H_PRIMARY * 5)
check("label-bound cutoff dogru", m.sum() == ((ts <= cutoff)).sum(), f"m={m.sum()}")
check("cutoff icinde Y tanimli", labs["future_return"].iloc[m.to_numpy()].notna().all())

# 3) loader koruması: FINAL pencereleri guard'lar (küçük sahte frame üzerinde)
from src.freqai.p5_splits import check_not_in_protected, HoldoutLeakError
ok = False
try:
    bad = pd.Series([FINAL_A_START, FINAL_B_START, FINAL_C_START, FINAL_P5_START])
    check_not_in_protected(bad, "test")
except HoldoutLeakError:
    ok = True
check("protected window leak -> HoldoutLeakError", ok)

# 4) split immutably: future_return + dates aligned ve TRAIN/VAL aralığında
from phase502_labels import build_frame, split_train_val_per_label
frame5 = build_frame()
check("5m frame 'date' + future_return kolonu", {"date", "future_return"} <= set(frame5.columns),
      f"cols={list(frame5.columns)[:8]}...")
d = split_train_val_per_label(frame5, "L1", "B0")
check("split return anahtarları", {"X_train", "y_train", "X_val", "y_val",
                                   "y_future_val", "val_dates", "n_train", "n_val"}
      <= set(d.keys()))
ts_val = pd.to_datetime(d["val_dates"])
check("val aralığı VAL_START..VAL_END", (ts_val.min() >= VAL_START) and (ts_val.max() <= VAL_END))
check("val train üzerinde", (len(d["y_val"]) == d["n_val"])
      and (len(d["y_train"]) == d["n_train"]))
# lookahead: X_val, y_val, y_future_val aynı uzunlukta farklı dönemler
check("y_future_val boyu == val", len(d["y_future_val"]) == len(d["y_val"]))
check("baseline pos rate L1 < 0.5", d["y_val"].mean() < 0.5,
      f"pos={d['y_val'].mean():.4f}")
check("expected_dropped warmup+H", expected_dropped(5) == 199 + H_PRIMARY
      and expected_dropped(15) == 199 + H_SECONDARY_15M)

print()
fails = [n for n, c in PASSED if not c]
print(f"TOPLAM: {len(PASSED)} test, {len(fails)} hatalı")
assert not fails, fails
print("ALL PASS")