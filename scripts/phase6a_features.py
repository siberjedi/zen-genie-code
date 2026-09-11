"""Phase 6A — cross-asset feature builder (FINAL LOCK §5/§6/§7/§8/§9).

Grid: BTC 5m close zamanlari (load_dataset_slice; TRAIN+VAL only).
r(a,k,t) = close_a(t)/close_a(t-k) - 1, hizalanmis gridde.
F1 breadth_1 | F2 breadth_12 | F3 dispersion_12 (ddof=1, RF icin monoton
  donusum oldugundan M2 sonucunu degistirmez — raporda notlu) |
F4 btc_rel_12 | F5 ethbtc_chg_12 | F6 corr_regime (Pearson, trailing 288,
  min_periods=288, 21 parite ortalamasi).
Eksik bar -> satir DUSURME (doldurma yok). ileriye donuk op YOK.

Cikti: data/xa_features.parquet (date + 6 kolon) + coverage/drop raporu.
BTC serisi NEW kolonlarina GIRMEZ (assert).
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

DATA_DIR = ROOT / "experiments" / "phase_06_market_context" / "6A_cross_asset" / "data"
UNIVERSE = ["ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT", "BCHUSDT"]
XA_COLS = ["breadth_1", "breadth_12", "dispersion_12", "btc_rel_12",
           "ethbtc_chg_12", "corr_regime"]
CORR_WINDOW = 288


def rolling_mean_pairwise_corr(ret, window=CORR_WINDOW):
    """Trailing pencere Pearson korelasyonlarinin 21 parite ortalamasi.

    ret: (n, p) float array; pencerede TEK NaN varsa cikti NaN
    (min_periods=window esdegeri). Tam vektorize, chunk'li (bellek sinirli).
    """
    n, p = ret.shape
    out = np.full(n, np.nan)
    iu = np.triu_indices(p, k=1)
    CH = 20000
    for s in range(0, n, CH):
        e = min(n, s + CH)
        lo = max(0, s - window + 1)
        seg = ret[lo:e]
        m = seg.shape[0]
        if m < window:
            continue
        w = np.lib.stride_tricks.sliding_window_view(seg, window, axis=0)
        w = np.ascontiguousarray(w.transpose(0, 2, 1))  # (nwin, window, p)
        bad = np.isnan(w).any(axis=(1, 2))
        zf = np.where(np.isnan(w), 0.0, w)
        zf = zf - zf.mean(axis=1, keepdims=True)
        cov = (zf.transpose(0, 2, 1) @ zf) / (window - 1)
        d = np.sqrt(np.diagonal(cov, axis1=1, axis2=2))
        denom = d[:, :, None] * d[:, None, :]
        with np.errstate(invalid="ignore", divide="ignore"):
            corr = np.where(denom > 0, cov / np.maximum(denom, 1e-300), np.nan)
        mc = np.array([np.nanmean(corr[i][iu]) for i in range(corr.shape[0])])
        mc[bad] = np.nan
        start_row = lo + window - 1
        out[start_row:e] = mc[:e - start_row]
    return out


def causality_probe_xa():
    """Bu modulde ileriye bakan op yok (kaynak taramasi)."""
    import inspect
    import phase6a_features as _self  # noqa
    src = inspect.getsource(build_features)
    for bad in (".shift(-", "ewm(center="):
        assert bad not in src, f"yasak operator: {bad}"


def build_features(btc_grid, closes, symbols=None):
    """btc_grid: DataFrame[date, btc_close]; closes: dict sym -> close array
    (btc_grid ile ayni sira/uzunlukta, eksikler NaN). DataFrame[6 kolon] dondurur.

    symbols: universe alt kumesi (LOO exploratory icin); None -> kilitli 7'li.
    Primary deneyde SADECE None kullanilir (lock §6 exact).
    """
    syms = list(symbols) if symbols else list(UNIVERSE)
    n = len(btc_grid)
    for sym in syms:
        arr = closes[sym]
        assert len(arr) == n, f"uzunluk uyumsuz: {sym}"
        assert sym != "BTCUSDT", "BTC universe disi olmali"
    C = {s: np.asarray(closes[s], float) for s in syms}
    btc = np.asarray(btc_grid["btc_close"], float)
    eth = C["ETHUSDT"]  # F5 numeraire (LOO'da ETH dusurulmez, raporda notlu)

    def R(arr, k):
        out = np.full(n, np.nan)
        ok = (arr[k:] > 0) & (arr[:-k] > 0)
        out[k:][ok] = arr[k:][ok] / arr[:-k][ok] - 1.0
        return out

    R1 = {s: R(C[s], 1) for s in syms}
    R12 = {s: R(C[s], 12) for s in syms}
    M1 = np.column_stack([R1[s] for s in syms])
    M12 = np.column_stack([R12[s] for s in syms])
    out = pd.DataFrame(index=btc_grid.index)
    mask1 = np.isnan(M1).any(axis=1)
    mask12 = np.isnan(M12).any(axis=1)
    b1 = (M1 > 0).mean(axis=1)
    b1[mask1] = np.nan
    b12 = (M12 > 0).mean(axis=1)
    b12[mask12] = np.nan
    out["breadth_1"] = b1
    out["breadth_12"] = b12
    out["dispersion_12"] = np.std(M12, axis=1, ddof=1)
    out["btc_rel_12"] = R(btc, 12) - np.mean(M12, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = eth / btc
    out["ethbtc_chg_12"] = R(ratio, 12)
    out["corr_regime"] = rolling_mean_pairwise_corr(M1, CORR_WINDOW)
    return out[XA_COLS]


def main():
    btc = load_dataset_slice()[["date", "close"]].rename(columns={"close": "btc_close"})
    btc = btc.reset_index(drop=True)
    ts = pd.to_datetime(btc["date"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    # birim-bagimsiz ms: datetime64[ms] (pandas3) veya [ns] farketmez
    btc_ms = to_ms(ts)
    closes = {}
    drop_report = {}
    for sym in UNIVERSE:
        df = pd.read_parquet(DATA_DIR / f"xa_{sym}.parquet")
        m = dict(zip(df["open_ms"].to_numpy(), df["close"].to_numpy()))
        arr = np.array([m.get(int(ms), np.nan) for ms in btc_ms], float)
        closes[sym] = arr
        drop_report[sym] = int(np.isnan(arr).sum())
    print("eksik-bar (drop) sayisi:", drop_report, flush=True)
    feats = build_features(btc, closes)
    # BTC sizinti assert'i (lock §9-4): NEW kolu SADECE 6 kilitli familyadan
    # olusur; B0-B3 blok kolonu giremez. (F4/F5 BTC'yi numeraire olarak
    # kullanir — lock §6 ile baglayici; yasak olan B0-tipi BTC-oz momentumdur.)
    from phase501_features import FEATURE_UNION
    assert list(feats.columns) == XA_COLS
    assert not (set(feats.columns) & set(FEATURE_UNION)), "blok kolonu sizdi"
    assert not np.isinf(feats.to_numpy()).any()
    out = pd.DataFrame({"date": pd.to_datetime(btc["date"])})
    out = pd.concat([out, feats], axis=1)
    out.to_parquet(DATA_DIR / "xa_features.parquet", index=False)
    nan_counts = {c: int(out[c].isna().sum()) for c in XA_COLS}
    print("NaN sayilari:", nan_counts, flush=True)
    print(f"YAZILDI: xa_features.parquet {out.shape}", flush=True)


if __name__ == "__main__":
    main()
