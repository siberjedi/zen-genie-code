"""Phase 5 — FINAL_TEST_P5 holdout bağımsız doğrulama + guard testleri.

AŞAMA 2/3/4 teyidi. NO TRAINING · NO EVALUATION.
Guard testleri: korunan pencerelere sızıntı denemesi ABORT etmeli.
Final B / C verisi indirilmediği, mevcut 2020-2023 feather'in dokunulmadığı teyit edilir.
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

HOLDOUT = ROOT / "experiments" / "phase_05_ml" / "holdout" / "BTC_USDT-5m_2025H1.feather"
MANIFEST = ROOT / "experiments" / "phase_05_ml" / "holdout" / "manifest_2025H1.json"
EXISTING = ROOT / "freqtrade" / "user_data" / "data" / "binance" / "BTC_USDT-5m.feather"

EXPECTED_ROWS = 52128
EXPECTED_SHA = "2441bf175f86b3f6d52246d482bb9263a49684831387bfed504b91a9fab5389c"

from src.freqai.p5_splits import (
    check_not_in_protected, load_holdout, HoldoutLeakError, verify_holdout_hash,
    FINAL_B_START, FINAL_B_END, FINAL_C_START, FINAL_C_END,
)

results = {}


def chk(name, cond, detail=""):
    results[name] = (bool(cond), detail)
    print(f"[{'OK' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


# --- hash / dosya ---
chk("holdout_dosya_var", HOLDOUT.exists())
sha = hashlib.sha256(HOLDOUT.read_bytes()).hexdigest() if HOLDOUT.exists() else ""
chk("sha256_pin", sha == EXPECTED_SHA, sha)
chk("manifest_var", MANIFEST.exists())

# --- veri doğrulama ---
if HOLDOUT.exists():
    df = pd.read_feather(HOLDOUT)
    chk("schema_kolonlar", list(df.columns) == ["date", "open", "high", "low", "close", "volume"])
    chk("row_count", len(df) == EXPECTED_ROWS, f"{len(df)}")
    chk("duplicate_yok", int(df["date"].duplicated().sum()) == 0)
    chk("null_yok", int(df.isna().sum().sum()) == 0)
    ts = pd.to_datetime(df["date"])
    chk("date_utc", ts.dt.tz is not None)
    chk("date_first", ts.iloc[0] == pd.Timestamp("2025-01-01", tz="UTC"), str(ts.iloc[0]))
    chk("date_last", ts.iloc[-1] == pd.Timestamp("2025-06-30 23:55", tz="UTC"), str(ts.iloc[-1]))
    # ordering
    chk("ordering_monotonik", ts.is_monotonic_increasing)
    # tam 5m grid (missing interval)
    grid = pd.date_range("2025-01-01", "2025-06-30 23:55", freq="5min", tz="UTC")
    chk("missing_interval_yok", (grid.difference(ts)).shape[0] == 0,
        f"eksik_mum={grid.difference(ts).shape[0]}")
    # OHLCV integrity
    chk("fiyat_pozitif",
        int((df[["open", "high", "low", "close"]].le(0)).sum().sum()) == 0)
    chk("ohlc_ilişki",
        int(((df["high"] < df[["open", "close", "low"]].max(axis=1)) |
             (df["low"] > df[["open", "close", "high"]].min(axis=1))).sum()) == 0)

# --- guard testleri ---
guard = {"guard_train_val_serisi_ok": None, "guard_final_b_rej": None,
         "guard_final_p5_rej": None, "guard_hash_pin": None}
try:
    serie = pd.Series(pd.date_range("2022-06-01", "2023-06-30", freq="1D", tz="UTC"))
    check_not_in_protected(serie, "test-trainval")
    ok = True
except HoldoutLeakError:
    ok = False
guard["guard_train_val_serisi_ok"] = ok
chk("guard_train_val_ok", ok)

# Final B (2024H1) erişim denemesi ABORT etmeli
try:
    b = pd.Series(pd.date_range("2024-03-01", "2024-03-05", freq="1D", tz="UTC"))
    check_not_in_protected(b, "final-B-deneme")
    guard["guard_final_b_rej"] = False
    chk("guard_final_b_rej", False, "ABORT ETMEDİ — SORUN")
except HoldoutLeakError as e:
    guard["guard_final_b_rej"] = True
    chk("guard_final_b_rej", True, str(e)[:60])

# FINAL_P5 erişim denemesi ABORT etmeli
try:
    p = pd.Series(pd.date_range("2025-03-01", "2025-03-05", freq="1D", tz="UTC"))
    check_not_in_protected(p, "final-P5-deneme")
    guard["guard_final_p5_rej"] = False
    chk("guard_final_p5_rej", False, "ABORT ETMEDİ — SORUN")
except HoldoutLeakError as e:
    guard["guard_final_p5_rej"] = True
    chk("guard_final_p5_rej", True, str(e)[:60])

# hash pin
try:
    verify_holdout_hash()
    guard["guard_hash_pin"] = True
    chk("guard_hash_pin", True)
except Exception as e:
    guard["guard_hash_pin"] = False
    chk("guard_hash_pin", False, str(e))

# FINAL C (2024H2) koruma
try:
    c = pd.Series(pd.date_range("2024-09-01", "2024-09-05", freq="1D", tz="UTC"))
    check_not_in_protected(c, "final-C-deneme")
    guard["guard_final_c_rej"] = False
    chk("guard_final_c_rej", False, "ABORT ETMEDİ — SORUN")
except HoldoutLeakError:
    guard["guard_final_c_rej"] = True
    chk("guard_final_c_rej", True)

# load_holdout: pencerenin tam 2025H1 olduğunu teyit eder (abart tekrar)
# --- Final B / C verisi indirilmedi / mevcut dataset dokunulmadı ---
binance_dir = ROOT / "freqtrade" / "user_data" / "data" / "binance"
yearly_files = [p.name for p in binance_dir.glob("*2024*")] + [p.name for p in binance_dir.glob("*2025*")]
chk("finalB_C_veri_yok", len([x for x in sorted(binance_dir.iterdir()) if "2024" in x.name]) == 0,
    f"4m-files={[x.name for x in binance_dir.iterdir() if '2024' in x.name]}")
chk("mevcut_dataset_var", EXISTING.exists())
if EXISTING.exists():
    ex = pd.read_feather(EXISTING)
    chk("mevcut_dataset_max_tarih", ex["date"].max() <= pd.Timestamp("2023-12-31 23:55", tz="UTC"),
        str(ex["date"].max()))
    chk("mevcut_dataset_boyut", len(ex) == 420014, f"{len(ex)}")

# --- manifest özeti ---
summary = {
    "holdout": {k: (v[0], v[1]) for k, v in results.items()},
    "guards": guard,
    "all_pass": all(v[0] for v in results.values()) and all(guard.values()),
}
out = ROOT / "experiments" / "phase_05_ml" / "holdout" / "verify_2025H1.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
print("\nALL PASS" if summary["all_pass"] else "\nHAS FAILURES")
print("verify_out:", out)