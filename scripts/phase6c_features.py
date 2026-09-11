"""Phase 6C — OI feature builder (FINAL LOCK §6/§7/§8/§9/§10).

Grid: BTC 5m close zamanlari. OI(t) = create_time <= t son snapshot
(asof-backward, exact-ms, yuvarlama yok).
F1 oi_chg_12  = (OI(t)-OI(t-12))/OI(t-12)
F2 oi_z_288   = (OI(t)-mean_288)/std_288(ddof=1, min_periods=288)
F3 oi_price_div = sign(r_btc_12) * sign(oi_chg_12)  (+1/-1/0)
F4 oi_chg_1   = (OI(t)-OI(t-1))/OI(t-1)
F5 oi_range_288 = (OI(t)-min_288)/(max_288-min_288) ; max==min -> 0.5 (kilitli)
Eksik snapshot -> satir DUSURME (doldurma yok).

Cikti: data/oi_features.parquet (date + 5 kolon).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.timeconv import to_ms

from phase502_labels import load_dataset_slice

DATA_DIR = ROOT / "experiments" / "phase_06_market_context" / "6C_oi" / "data"
OI_COLS = ["oi_chg_12", "oi_z_288", "oi_price_div", "oi_chg_1", "oi_range_288"]


def causality_probe_oc():
    import inspect
    import phase6c_features as _self  # noqa
    src = inspect.getsource(build_features)
    for bad in (".shift(-", "ewm(center="):
        assert bad not in src, f"yasak operator: {bad}"


def build_features(oi_grid, btc_close):
    """oi_grid: (n,) float (NaN = snapshot yok); btc_close: (n,) float.
    DataFrame[5 kolon] dondurur."""
    oi = np.asarray(oi_grid, float)
    bc = np.asarray(btc_close, float)
    n = len(oi)
    assert len(bc) == n
    out = pd.DataFrame(index=range(n))

    def _chg(arr, k):
        o = np.full(n, np.nan)
        ok = (arr[k:] > 0) & (arr[:-k] > 0)
        o[k:][ok] = arr[k:][ok] / arr[:-k][ok] - 1.0
        return o

    c12 = _chg(oi, 12)
    c1 = _chg(oi, 1)
    out["oi_chg_12"] = c12
    out["oi_chg_1"] = c1
    s = pd.Series(oi)
    mu = s.rolling(288, min_periods=288).mean().to_numpy()
    sd = s.rolling(288, min_periods=288).std(ddof=1).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        out["oi_z_288"] = np.where(sd > 0, (oi - mu) / sd, np.nan)
    rb = _chg(bc, 12)
    out["oi_price_div"] = np.sign(rb) * np.sign(c12)
    mn = s.rolling(288, min_periods=288).min().to_numpy()
    mx = s.rolling(288, min_periods=288).max().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        rng = np.where(mx > mn, (oi - mn) / (mx - mn), 0.5)
    rng[np.isnan(oi)] = np.nan
    # min/max penceresi NaN ise (warmup) -> NaN
    rng[np.isnan(mn) | np.isnan(mx)] = np.nan
    out["oi_range_288"] = rng
    return out[OI_COLS]


def main():
    oi = pd.read_parquet(DATA_DIR / "oi_btcusdt.parquet")
    oi = oi.sort_values("create_ms").reset_index(drop=True)
    btc = load_dataset_slice()[["date", "close"]].reset_index(drop=True)
    ts = pd.to_datetime(btc["date"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    btc_ms = to_ms(ts)
    # asof-backward: son create_ms <= t
    fms = oi["create_ms"].to_numpy(dtype="int64")
    assert (np.diff(fms) > 0).all(), "STOP: snapshot sirasi bozuk"
    idx = np.searchsorted(fms, btc_ms.astype("int64"), side="right") - 1
    grid = np.full(len(btc_ms), np.nan)
    ok = idx >= 0
    grid[ok] = oi["oi"].to_numpy()[idx[ok]]
    n_before_first = int((~ok).sum())
    print(f"ilk snapshot oncesi bar (drop): {n_before_first}", flush=True)
    feats = build_features(grid, btc["close"].to_numpy())
    assert list(feats.columns) == OI_COLS
    assert not np.isinf(feats.to_numpy()).any()
    from phase501_features import FEATURE_UNION
    assert not (set(feats.columns) & set(FEATURE_UNION)), "blok kolonu sizdi"
    out = pd.DataFrame({"date": ts})
    out = pd.concat([out, feats], axis=1)
    out.to_parquet(DATA_DIR / "oi_features.parquet", index=False)
    print("NaN:", {c: int(out[c].isna().sum()) for c in OI_COLS}, flush=True)
    print(f"YAZILDI: oi_features.parquet {out.shape}", flush=True)


if __name__ == "__main__":
    main()
