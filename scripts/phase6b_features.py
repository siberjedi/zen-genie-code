"""Phase 6B — funding feature builder (FINAL LOCK §5/§6/§7/§8/§9).

Settlement serisi (settlement-endeksli, 8h):
  R[j] j. settlement orani.
F1 fund_rate   = R[j*(t)]
F2 fund_z_30   = (R[j*] - mean(R[j*-29..j*])) / std(ddof=1)  (min_periods=30)
F3 fund_sign   = sign(R[j*])  (0 -> 0)
F4 fund_abs_chg= |R[j*] - R[j*-1]|
F5 fund_persist= ayni-isaretli ardisi settlement sayisi, 8'de cap (0/sifir-reset)
j*(t) = son funding_ms <= t (asof-backward, ACTUAL ms — yuvarlama yok).
markPrice/predicted ASLA kullanilmaz (parse asamasinda atilir).

Cikti: data/fund_features.parquet (date + 5 kolon).
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

DATA_DIR = ROOT / "experiments" / "phase_06_market_context" / "6B_funding" / "data"
FUND_COLS = ["fund_rate", "fund_z_30", "fund_sign", "fund_abs_chg", "fund_persist"]
PERSIST_CAP = 8
Z_WINDOW = 30


def causality_probe_fb():
    import inspect
    import phase6b_features as _self  # noqa
    src = inspect.getsource(build_features)
    for bad in (".shift(-", "ewm(center=", "predicted", "mark_price", "markPrice"):
        assert bad not in src, f"yasak operator: {bad}"


def settlement_features(rates):
    """Settlement-endeksli 5 vektor (numpy). rates: (m,) float."""
    r = np.asarray(rates, float)
    m = len(r)
    f1 = r.copy()
    mu = pd.Series(r).rolling(Z_WINDOW, min_periods=Z_WINDOW).mean().to_numpy()
    sd = pd.Series(r).rolling(Z_WINDOW, min_periods=Z_WINDOW).std(ddof=1).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        f2 = np.where(sd > 0, (r - mu) / sd, np.nan)
    f3 = np.sign(r)
    f4 = np.full(m, np.nan)
    f4[1:] = np.abs(r[1:] - r[:-1])
    f5 = np.zeros(m)
    run, prev = 0, 0.0
    for j in range(m):
        s = float(np.sign(r[j]))
        if s == 0.0 or np.isnan(r[j]):
            run, prev = 0, 0.0
            f5[j] = np.nan if np.isnan(r[j]) else 0.0
        elif s == prev:
            run = min(run + 1, PERSIST_CAP)
            f5[j] = run
        else:
            run, prev = 1, s
            f5[j] = 1.0
    return {"fund_rate": f1, "fund_z_30": f2, "fund_sign": f3,
            "fund_abs_chg": f4, "fund_persist": f5}


def build_features(btc_ms, fund_ms, rates):
    """Candle gridine asof-backward esleme. Donus: DataFrame[5 kolon]."""
    fund_ms = np.asarray(fund_ms, dtype="int64")
    assert (np.diff(fund_ms) > 0).all(), "settlement sirasi bozuk"
    idx = np.searchsorted(fund_ms, np.asarray(btc_ms, dtype="int64"), side="right") - 1
    feats = settlement_features(rates)
    out = pd.DataFrame(index=range(len(btc_ms)))
    for c in FUND_COLS:
        col = np.full(len(btc_ms), np.nan)
        ok = idx >= 0
        col[ok] = feats[c][idx[ok]]
        out[c] = col
    return out[FUND_COLS]


def main():
    fund = pd.read_parquet(DATA_DIR / "funding_btcusdt.parquet")
    fund = fund.sort_values("funding_ms").reset_index(drop=True)
    btc = load_dataset_slice()[["date"]].reset_index(drop=True)
    ts = pd.to_datetime(btc["date"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    btc_ms = to_ms(ts)
    assert btc_ms.max() < pd.Timestamp("2023-07-01", tz="UTC").value // 10**6, "grid tasmasi"
    feats = build_features(btc_ms, fund["funding_ms"].to_numpy(),
                           fund["funding_rate"].to_numpy())
    assert list(feats.columns) == FUND_COLS
    assert not np.isinf(feats.to_numpy()).any()
    # NEW-kolon sartnamesi: 5 kilitli familya, blok kolonu yok
    from phase501_features import FEATURE_UNION
    assert not (set(feats.columns) & set(FEATURE_UNION)), "blok kolonu sizdi"
    out = pd.DataFrame({"date": ts})
    out = pd.concat([out, feats], axis=1)
    out.to_parquet(DATA_DIR / "fund_features.parquet", index=False)
    print("NaN:", {c: int(out[c].isna().sum()) for c in FUND_COLS}, flush=True)
    print(f"YAZILDI: fund_features.parquet {out.shape}", flush=True)


if __name__ == "__main__":
    main()
