"""Phase 5 — Labels L0/L1/L2 + TRAIN/VAL split (kilitli, DESIGN 500 sec 5/6/8).

- Y(t) = close[t+H]/close[t] - 1 (H mum ileride). Base = close[t]; forward t+1..t+H.
- L0 = Y > 0 ; L1 = Y > C (C = 0.003 round-trip: fee 0.001*2 + slip 5bps*2);
  L2 = Y (regresyon).
- Off-by-one guard: forward pencere base mumu ASLA içermez (diff ile close index farki).
- Label-bound kurali (Phase 3 slice_frame): pencere sonundan H mum siniri; val label
  ları FINAL_A'ya, train label'lari VAL'e TASMAZ.
- Loader: yalnizca 2020-01-01..2023-06-30 23:55 (VAL_END). FINAL_B/C/P5/A erisilmez.
"""
import numpy as np
import pandas as pd

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.freqai.p5_splits import (TRAIN_START, TRAIN_END, VAL_START, VAL_END,
                                  check_not_in_protected)

COST_C = 0.003  # DESIGN 500 sec 14: 2*(fee 0.001 + slip 0.0005)
TF_MINUTES = 5
H_PRIMARY = 12        # 5m -> ~1 saat
H_SECONDARY_15M = 12  # 15m -> 3 saat
FEATHER = "freqtrade/user_data/data/binance/BTC_USDT-5m.feather"

LABELS = ["L0", "L1", "L2"]


def load_dataset_slice() -> pd.DataFrame:
    """5m feather'i yalnizca TRAIN+VAL araliginda yukler (2020-01-01..2023-06-30 23:55).

    Hiçbir korunan pencere (FINAL_A/B/C/P5) bu yukleyicinin kapsaminda degildir;
    ortaya kayan veri feather'da olsa bile yuklenmez (guard net).
    """
    df = pd.read_feather(FEATHER)
    need = {"date", "open", "high", "low", "close", "volume"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"eksik kolonlar: {sorted(missing)}")
    ts = pd.to_datetime(df["date"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    df["date"] = ts
    m = (ts >= TRAIN_START) & (ts <= VAL_END)
    out = df.loc[m].reset_index(drop=True)
    check_not_in_protected(out["date"], "loader-slice")
    return out


def compute_labels(df: pd.DataFrame, horizon: int = H_PRIMARY) -> pd.DataFrame:
    """close serisinden Y + L0/L1/L2. Index korunur; son `horizon` satir NaN."""
    close = df["close"].astype(float)
    future = close.shift(-horizon) / close - 1.0  # base mum forward'ta DEGIL
    out = pd.DataFrame(index=df.index)
    out["future_return"] = future
    out["L0"] = (future > 0.0).astype(float)
    out["L1"] = (future > COST_C).astype(float)
    out["L2"] = future
    for col in ("L0", "L1", "L2"):
        out.loc[future.isna(), col] = np.nan
    return out


def label_bound_mask(dates: pd.Series, start, end, horizon: int,
                     tf_minutes: int = TF_MINUTES) -> pd.Series:
    """Pencere [start, end] icinde label'i TANIMLI satirlar (end - H*tf siniri)."""
    ts = pd.to_datetime(dates)
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if start_ts.tz is None:
        start_ts = start_ts.tz_localize("UTC")
    if end_ts.tz is None:
        end_ts = end_ts.tz_localize("UTC")
    cutoff = end_ts - pd.Timedelta(minutes=horizon * tf_minutes)
    return (ts >= start_ts) & (ts <= cutoff)


def build_frame(tf_minutes: int = TF_MINUTES, horizon: int = H_PRIMARY) -> pd.DataFrame:
    """OHLCV slice -> feature + label birlesik cekirdek (TRAIN+VAL).

    NaN satirlar (warmup + label kuyrugu) düsürülür; tarih kolonu korunur.
    Feature ve label AYNI tarih ekseninde hizalanir (index hizasi).
    """
    from phase501_features import build_features, resample_15m
    base = load_dataset_slice()
    if tf_minutes == 5:
        bars = base
    elif tf_minutes == 15:
        bars = resample_15m(base)
    else:
        raise ValueError(f"desteklenmeyen tf: {tf_minutes}")
    feats = build_features(bars).reset_index(drop=True)
    labs = compute_labels(bars, horizon).reset_index(drop=True)
    frame = feats.join(labs)
    frame["date"] = pd.to_datetime(bars["date"]).to_numpy()
    check_not_in_protected(frame["date"], f"frame[{tf_minutes}m]")
    return frame


def split_train_val_per_label(frame: pd.DataFrame, label: str, block: str | None = None,
                              tf_minutes: int = TF_MINUTES,
                              horizon: int = H_PRIMARY):
    """TRAIN/VAL (X, y, X_val, y_val, y_future_val, val_dates) dondurur.

    block None = tum 28 union kolonu (iseyarar için). label L0/L1/L2.
    train: SURDURME; val: 2023-01-01..VAL_END-H*tf (label sinirsiz).
    """
    from phase501_features import BLOCKS
    if block is None:
        cols = BLOCKS["B3"]
    else:
        cols = BLOCKS[block]
    if label not in LABELS:
        raise ValueError(f"bilinmeyen label: {label}")
    ts = pd.to_datetime(frame["date"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    train_mask = label_bound_mask(ts, TRAIN_START, TRAIN_END, horizon, tf_minutes)
    val_mask = label_bound_mask(ts, VAL_START, VAL_END, horizon, tf_minutes)
    tr = frame.loc[train_mask].copy()
    va = frame.loc[val_mask].copy()
    check_not_in_protected(tr["date"], f"train[{label}]")
    check_not_in_protected(va["date"], f"val[{label}]")
    # NaN politikasi: doldurma yok, düsürme var (warmup + label kuyrugu + range=0)
    tr = tr.dropna(subset=cols + [label]).reset_index(drop=True)
    va = va.dropna(subset=cols + [label]).reset_index(drop=True)
    X_train = tr[cols].to_numpy()
    y_train = tr[label].to_numpy()
    X_val = va[cols].to_numpy()
    y_val = va[label].to_numpy()
    return {
        "X_train": X_train, "y_train": y_train,
        "X_val": X_val, "y_val": y_val,
        "y_future_val": va["future_return"].to_numpy(),
        "val_dates": va["date"].to_numpy(),
        "n_train": len(tr), "n_val": len(va),
    }


def expected_dropped(tf_minutes: int = TF_MINUTES) -> int:
    """Mekanik kayıp: warmup (199) + label kuyrugu (H). 15m'de ayhan hesap."""
    return 199 + H_SECONDARY_15M if tf_minutes == 15 else 199 + H_PRIMARY


if __name__ == "__main__":
    from phase501_features import BLOCKS
    frame5 = build_frame()
    print(f"5m frame: {frame5.shape} (nansiz drop sonrasi)")
    for lb in LABELS:
        for b in ("B0", "B1", "B2", "B3"):
            d = split_train_val_per_label(frame5, lb, b)
            print(f"  {lb} {b}: train={d['n_train']} val={d['n_val']} "
                  f"val_pos={(d['y_val'] > 0.5).mean():.4f}")
    frame15 = build_frame(tf_minutes=15, horizon=H_SECONDARY_15M)
    print(f"15m frame: {frame15.shape}")
    for lb in ("L0", "L1"):
        for b in ("B1", "B3"):
            d = split_train_val_per_label(frame15, lb, b, tf_minutes=15,
                                          horizon=H_SECONDARY_15M)
            print(f"  15m {lb} {b}: train={d['n_train']} val={d['n_val']}")