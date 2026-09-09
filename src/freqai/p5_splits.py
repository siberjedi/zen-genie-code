"""Phase 5 — FINAL_TEST_P5 holdout rezervasyonu + koruma sabitleri (kilitli, 2026-09-07).

M.20 formalization: Phase 5 holdout = 2025H1 (2025-01-01 -> 2025-06-30).
- TRAIN:      2020-01-01 -> 2022-12-31  (mevcut dataset, DOKUNULMAZ)
- VALIDATION: 2023-01-01 -> 2023-06-30  (mevcut dataset, DOKUNULMAZ)
- FINAL_P5:   2025-01-01 -> 2025-06-30  (RESERVED — yalnızca tek FINAL değerlendirme)
Korunan pencereler (hiçbir Phase 5 script'i erişemez):
- FINAL_B: 2024-01-01 -> 2024-06-30  (RL final — UNTOUCHED)
- FINAL_C: 2024-07-01 -> 2024-12-31  (karşılaştırma — UNTOUCHED)
- FINAL_A: 2023-07-01 -> 2023-12-31  (FreqAI — TÜKETILDİ, kullanılamaz)
"""
import hashlib
import json
from pathlib import Path

import pandas as pd

# --- Rezerve pencereler ---
TRAIN_START = pd.Timestamp("2020-01-01", tz="UTC")
TRAIN_END = pd.Timestamp("2022-12-31", tz="UTC")
VAL_START = pd.Timestamp("2023-01-01", tz="UTC")
VAL_END = pd.Timestamp("2023-06-30", tz="UTC")

FINAL_A_START = pd.Timestamp("2023-07-01", tz="UTC")
FINAL_A_END = pd.Timestamp("2023-12-31 23:55", tz="UTC")
FINAL_B_START = pd.Timestamp("2024-01-01", tz="UTC")
FINAL_B_END = pd.Timestamp("2024-06-30 23:55", tz="UTC")
FINAL_C_START = pd.Timestamp("2024-07-01", tz="UTC")
FINAL_C_END = pd.Timestamp("2024-12-31 23:55", tz="UTC")

# PHASE 5 HOLDOUT (M.20)
FINAL_P5_START = pd.Timestamp("2025-01-01 00:00", tz="UTC")
FINAL_P5_END = pd.Timestamp("2025-06-30 23:55", tz="UTC")

TF_MINUTES = 5  # 5m
H12_MINUTES = 12 * TF_MINUTES  # label forward sınırı (bölüm 8: t+1..t+H)

# 2025H1 holdout dosyası + hash pin (manifest ile eşleşmeli)
HOLDOUT_DIR = Path(__file__).resolve().parents[2] / "experiments" / "phase_05_ml" / "holdout"
HOLDOUT_FEATHER = HOLDOUT_DIR / "BTC_USDT-5m_2025H1.feather"
HOLDOUT_MANIFEST = HOLDOUT_DIR / "manifest_2025H1.json"
HOLDOUT_SHA256 = "2441bf175f86b3f6d52246d482bb9263a49684831387bfed504b91a9fab5389c"

PROTECTED = [
    ("FINAL_A", FINAL_A_START, FINAL_A_END),
    ("FINAL_B", FINAL_B_START, FINAL_B_END),
    ("FINAL_C", FINAL_C_START, FINAL_C_END),
    ("FINAL_P5", FINAL_P5_START, FINAL_P5_END),
]


class HoldoutLeakError(AssertionError):
    """Korunan pencereye (FINAL_P5 / B / C / A) erişim denemesi."""


class HoldoutHashError(AssertionError):
    """Pinlenmiş holdout hash'i değişti — veriye dokunuldu."""


def check_not_in_protected(dates: pd.Series, context: str = "") -> None:
    """Serideki hiçbir tarih korunan pencerelerden birinde olmamalı. ABORT."""
    ts = pd.to_datetime(dates)
    if getattr(ts, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC") if hasattr(ts, "dt") and ts.dt.tz is None else ts
    # tz-normalize: naive ise UTC kabul et
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize("UTC")
    for name, start, end in PROTECTED:
        bad = ts[(ts >= start) & (ts <= end)]
        if len(bad):
            raise HoldoutLeakError(
                f"[{context}] {name} penceresine sızıntı: {len(bad)} satır "
                f"({bad.min()} -> {bad.max()}). ABORT.")


def split_train_val_p5(df: pd.DataFrame, date_col: str = "date"):
    """TRAIN/VAL ayrımı (yalnızca seçim için) + koruma guard'ı."""
    check_not_in_protected(df[date_col], "split-girdi")
    ts = pd.to_datetime(df[date_col])
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize("UTC")
    train = df[(ts >= TRAIN_START) & (ts <= TRAIN_END)].reset_index(drop=True)
    val = df[(ts >= VAL_START) & (ts <= VAL_END)].reset_index(drop=True)
    if len(train) == 0 or len(val) == 0:
        raise ValueError(f"bos split: train={len(train)} val={len(val)}")
    return train, val


def verify_holdout_hash() -> str:
    """Holdout feather'ının SHA256'sını pin ile karşılaştır. Uyuşmazlık = ABORT."""
    if not HOLDOUT_FEATHER.exists():
        raise FileNotFoundError(f"holdout yok: {HOLDOUT_FEATHER}")
    h = hashlib.sha256(HOLDOUT_FEATHER.read_bytes()).hexdigest()
    if h != HOLDOUT_SHA256:
        raise HoldoutHashError(
            f"holdout hash uyusmadi: {h} (pin {HOLDOUT_SHA256}). Veriye dokunuldu. ABORT.")
    return h


def load_holdout() -> pd.DataFrame:
    """Yalnızca FINAL değerlendirme hattının kullanacağı yükleyici (pin + pencere abart)."""
    verify_holdout_hash()
    df = pd.read_feather(HOLDOUT_FEATHER)
    ts = pd.to_datetime(df["date"])
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize("UTC")
    if (ts < FINAL_P5_START).any() or (ts > FINAL_P5_END).any():
        raise HoldoutLeakError("holdout penceresi dışında veri — FINAL_P5 aralığı ihlali.")
    df["date"] = ts
    return df


def holdout_status() -> dict:
    """Rapor için güncel durum."""
    return {
        "reservation": "FINAL_TEST_P5",
        "window": f"{FINAL_P5_START.date()} -> {FINAL_P5_END.date()}",
        "pin_sha256": HOLDOUT_SHA256,
        "file": str(HOLDOUT_FEATHER),
        "protected_untouchable": ["FINAL_A", "FINAL_B", "FINAL_C", "FINAL_P5"],
        "manifest": HOLDOUT_MANIFEST.exists(),
    }