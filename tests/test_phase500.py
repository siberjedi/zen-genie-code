"""Phase 5 — Holdout koruma testleri (plain-python runner).

Kapsam: FINAL_TEST_P5 (2025H1) rezervasyon doğrulama, hash pin, korunan
pencereler (A/B/C/P5) sızıntı guard'ı, split guard, mevcut dataset
dokunulmazlığı, holdout yükleyici pencere abartı.

Calistir: py -3 tests/test_phase500.py
"""
import hashlib
import pathlib
import sys

TESTROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(TESTROOT))

import pandas as pd

from src.freqai.p5_splits import (
    FINAL_P5_START, FINAL_P5_END, FINAL_B_START, FINAL_B_END,
    FINAL_C_START, FINAL_C_END, FINAL_A_START, FINAL_A_END,
    HOLDOUT_SHA256, HOLDOUT_FEATHER, HOLDOUT_MANIFEST,
    HoldoutLeakError, HoldoutHashError, check_not_in_protected,
    load_holdout, split_train_val_p5, verify_holdout_hash, PROTECTED,
)

PASSED = []


def check(name, cond, detail=""):
    PASSED.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not cond:
        raise AssertionError(name)


print("== 1. Rezervasyon sabitleri ==")
check("FINAL_P5=2025H1", FINAL_P5_START == pd.Timestamp("2025-01-01", tz="UTC")
      and FINAL_P5_END == pd.Timestamp("2025-06-30 23:55", tz="UTC"))
check("FINAL_B=2024H1 korunur", FINAL_B_START == pd.Timestamp("2024-01-01", tz="UTC")
      and FINAL_B_END == pd.Timestamp("2024-06-30 23:55", tz="UTC"))
check("FINAL_C=2024H2 korunur", FINAL_C_START == pd.Timestamp("2024-07-01", tz="UTC")
      and FINAL_C_END == pd.Timestamp("2024-12-31 23:55", tz="UTC"))
check("FINAL_A tüketildi (korumada)", any(n == "FINAL_A" for n, *_ in PROTECTED))

print("== 2. Hash pin ==")
check("holdout dosya var", HOLDOUT_FEATHER.exists())
if HOLDOUT_FEATHER.exists():
    sha = hashlib.sha256(HOLDOUT_FEATHER.read_bytes()).hexdigest()
    check("sha256 pin eşleşti", sha == HOLDOUT_SHA256, sha[:16])
    check("manifest var", HOLDOUT_MANIFEST.exists())
    try:
        h = verify_holdout_hash()
        check("verify_holdout_hash", h == HOLDOUT_SHA256)
    except Exception as e:
        check("verify_holdout_hash", False, str(e))

print("== 3. Sızıntı guard'ı (her korunan pencere için) ==")
for name, start, end in PROTECTED:
    probe = pd.Series([start + pd.Timedelta(days=1), start + pd.Timedelta(days=2)])
    try:
        check_not_in_protected(probe, f"guard-{name}")
        check(f"guard_{name}_abort", False, "ABORT ETMEDI")
    except HoldoutLeakError:
        check(f"guard_{name}_abort", True)
    except Exception:
        check(f"guard_{name}_abort", False, "yanlis exception")

print("== 4. Train/Val sınırı ve guard ==")
df = pd.DataFrame({"date": pd.Series([FINAL_P5_START])})
try:
    split_train_val_p5(df)
    check("split_final_p5_rej", False, "FINAL_P5 girerse ABORT etmeli")
except HoldoutLeakError:
    check("split_final_p5_rej", True)
except Exception as e:
    check("split_final_p5_rej", False, str(e)[:60])

toy = pd.DataFrame({"date": pd.date_range("2021-06-01", "2023-06-30", freq="1D", tz="UTC")})
tr, va = split_train_val_p5(toy)
check("train_kapsam", tr["date"].min() >= pd.Timestamp("2020-01-01", tz="UTC")
      and tr["date"].max() <= pd.Timestamp("2022-12-31", tz="UTC"))
check("val_kapsam", va["date"].min() >= pd.Timestamp("2023-01-01", tz="UTC")
      and va["date"].max() <= pd.Timestamp("2023-06-30", tz="UTC"))

print("== 5. Holdout yükleyici pencere ==")
h = load_holdout()
ts = pd.to_datetime(h["date"])
check("holdout min FINAL_P5", ts.min() == FINAL_P5_START)
check("holdout max FINAL_P5", ts.max() == FINAL_P5_END)
check("holdout 2025H1 aralığı", ((ts >= FINAL_P5_START) & (ts <= FINAL_P5_END)).all())

print("== 6. Bozuk hash reddi ==")
import src.freqai.p5_splits as p5
orig = p5.HOLDOUT_SHA256
p5.HOLDOUT_SHA256 = "0" * 64
try:
    verify_holdout_hash()
    check("hash_bozuk_rej", False, "ABORT etmeli")
except HoldoutHashError:
    check("hash_bozuk_rej", True)
except Exception as e:
    check("hash_bozuk_rej", False, str(e)[:40])
p5.HOLDOUT_SHA256 = orig

print()
fails = [n for n, c in PASSED if not c]
print(f"TOPLAM: {len(PASSED)} test, {len(fails)} hatalı")
assert not fails, fails
print("ALL PASS")