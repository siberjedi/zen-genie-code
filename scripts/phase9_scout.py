"""Phase 9 SCOUT — funding/basis carry olcumu (tasarim-dogrulama; KARAR YOK).

Kapsam: SADECE olcum. ML YOK, tuning YOK, threshold YOK (always-on),
backtest-strateji YOK (muhasebe defteri), holdout YOK (2020-2023H1 only).
GO/STOP = lock-onerisine devam/distop (islem degil).

 veri:
  - spot 5m: mevcut feather (TRAIN+VAL slice only)
  - perp 1h: Vision um monthly klines BTCUSDT 2020-01..2023-06 (bu script indirir;
    2023-07+ assert-YASAK) + CHECKSUM
  - funding: 6B arsivi (mevcut; yeniden indirilmez)
 muhasebe (1 BTC cifti, giris ilk bar, cikis son bar):
  - giris/cikis fee: spot taker %0.10 + perp taker %0.04 (donem tarifesi) + slip
    nominal 2bp/bacak/yon (preregistered-scout sayilari, raporda ayri gosterilir)
  - funding: settlement gunune atfedilir (00:00 yeni gune aittir); short alir (+)
  - basis P&L: [(perp-spot)_T - (perp-spot)_0] (long-spot/short-perp)
 leakage: settlement-sonrasi kullanim; eszamanli close'lar; ileri-bakis YOK.

Calistir: py -3 scripts/phase9_scout.py (arka planda + log)
"""
import hashlib
import io
import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from phase502_labels import load_dataset_slice
from src.timeconv import to_ms

D9 = ROOT / "experiments" / "phase_09_funding_basis" / "data"
UM = "https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1h"
SYM = "BTCUSDT"
Y0, Y1 = (2020, 1), (2023, 6)
FEE_SPOT, FEE_PERP, SLIP = 0.0010, 0.0004, 0.0002


def months():
    y, m = Y0
    out = []
    while (y, m) <= Y1:
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "zen-genie-p9/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def download_um():
    D9.mkdir(parents=True, exist_ok=True)
    frames, man = [], []
    for (y, m) in months():
        assert (y, m) <= Y1, "pencere disi"
        tag = f"{y}-{m:02d}"
        url = f"{UM}/{SYM}-1h-{tag}.zip"
        blob = fetch(url)
        chk = fetch(url + ".CHECKSUM").decode().strip().split()[0]
        if hashlib.sha256(blob).hexdigest() != chk:
            raise RuntimeError(f"STOP checksum: {tag}")
        zf = zipfile.ZipFile(io.BytesIO(blob))
        names = [n for n in zf.namelist() if n.endswith(".csv")]
        assert len(names) == 1
        raw = zf.read(names[0])
        first = pd.read_csv(io.BytesIO(raw), header=None, nrows=1)
        if str(first[0].iloc[0]).strip().lower() == "open_time":
            dh = pd.read_csv(io.BytesIO(raw))
            ot, cl = dh["open_time"].astype("int64"), dh["close"].astype(float)
        else:
            dh = pd.read_csv(io.BytesIO(raw), header=None)
            ot, cl = dh[0].astype("int64"), dh[4].astype(float)
        frames.append(pd.DataFrame({"open_ms": ot, "perp_close": cl}))
        man.append({"url": url, "sha256": chk, "rows": int(len(ot))})
    full = pd.concat(frames, ignore_index=True).sort_values("open_ms").reset_index(drop=True)
    assert full["open_ms"].is_monotonic_increasing and not full["open_ms"].duplicated().any()
    assert (full["perp_close"] > 0).all(), "STOP: non-positive perp"
    full.to_parquet(D9 / "um_btcusdt_1h.parquet", index=False)
    with open(D9 / "MANIFEST_UM_P9.json", "w", encoding="utf-8") as f:
        json.dump({"n_files": len(man), "n_bars": int(len(full)),
                   "first": str(pd.to_datetime(full["open_ms"].iloc[0], unit="ms", utc=True)),
                   "last": str(pd.to_datetime(full["open_ms"].iloc[-1], unit="ms", utc=True)),
                   "files": man}, f, indent=2)
    print(f"UM: {len(full)} bar", flush=True)
    return full


def main():
    t0 = time.time()
    um = download_um()
    spot5 = load_dataset_slice()[["date", "close"]]
    ts = pd.to_datetime(spot5["date"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    sms = to_ms(ts)
    # saat-basi spot close (perp 1h gridine hizala)
    um_ms = um["open_ms"].to_numpy()
    # HIZALAMA KURALI (dogrulanmis): UM 1h bar [T,T+1h) close ~ spot 5m [T+55dk]
    # close'una esittir (spot date = bar OPEN konvansiyonu). UM[T] <-> spot[T+55].
    # +0 kaydirma corr(diff)~0.09 verirken +55 corr(diff)~0.999 verir (amprik kanit).
    # Eszamanli-close disinda birlesme LEAKAGE/YANLILIK uretir.
    tgt = um_ms + 55 * 60 * 1000
    pos = np.searchsorted(sms, tgt)
    inb = pos < len(sms)
    ok = np.zeros(len(um_ms), bool)
    ok[inb] = sms[pos[inb]] == tgt[inb]
    _S = spot5["close"].to_numpy()[pos[ok]]
    _P = um["perp_close"].to_numpy()[ok]
    _c = float(np.corrcoef(np.diff(_S), np.diff(_P))[0, 1])
    assert _c > 0.99, f"STOP: hizalama bozuk (corr={_c:.4f})"
    print(f"hizalama corr(diff)={_c:.4f} (+55dk kurali)", flush=True)
    panel = pd.DataFrame({"ms": um_ms[ok], "perp": um["perp_close"].to_numpy()[ok],
                          "spot": spot5["close"].to_numpy()[pos[ok]]})
    assert (panel["spot"] > 0).all() and (panel["perp"] > 0).all()
    cov = len(panel) / len(um)
    print(f"hizalama coverage: {cov:.4f} ({len(panel)}/{len(um)})", flush=True)
    if cov < 0.99:
        raise RuntimeError("STOP: hizalama coverage dusuk")
    panel["basis"] = panel["perp"] - panel["spot"]
    panel["date"] = pd.to_datetime(panel["ms"], unit="ms", utc=True)
    # funding gunlugu (6B arsivi; settlement gunune ait)
    f6b = pd.read_parquet(ROOT / "experiments/phase_06_market_context/6B_funding/data/funding_btcusdt.parquet")
    fts = pd.to_datetime(f6b["funding_ms"], unit="ms", utc=True)
    fday = pd.DataFrame({"day": fts.dt.floor("D"), "rate": f6b["funding_rate"].to_numpy()})
    # carry defteri: 1 BTC cifti, giris ilk panel bari, cikis son
    p0, pT = panel["perp"].iloc[0], panel["perp"].iloc[-1]
    s0, sT = panel["spot"].iloc[0], panel["spot"].iloc[-1]
    fee_in = s0 * FEE_SPOT + p0 * FEE_PERP
    fee_out = sT * FEE_SPOT + pT * FEE_PERP
    slip = (s0 + p0 + sT + pT) * SLIP
    basis_pnl = (pT - sT) - (p0 - s0)
    # funding: short alir (oran>0); gunluk toplam x o gunku perp fiyati
    pmap = dict(zip(panel["ms"].to_numpy(), panel["perp"].to_numpy()))
    f_cash = 0.0
    for day, g in fday.groupby("day"):
        # o gunku settlement'larin toplami x gunun ilk perp fiyati (muhafazakar-yakin)
        px = panel.loc[panel["date"].dt.floor("D") == day, "perp"]
        if len(px) == 0:
            continue
        f_cash += float(g["rate"].sum()) * float(px.iloc[0])
    total = f_cash + basis_pnl - fee_in - fee_out - slip
    days = (panel["date"].iloc[-1] - panel["date"].iloc[0]).days
    ann = total / ((s0 + p0) / 2) / (days / 365) * 100
    # gunluk seri (MaxDD/tanimsal): funding gunluk + basis gunluk degisimi
    dly = panel.set_index("date").resample("1D").last()
    dly["f_day"] = fday.groupby("day")["rate"].sum()
    dly["basis_chg"] = dly["basis"].diff()
    pxd = dly["perp"]
    dly["f_cash"] = dly["f_day"] * pxd
    dly["net_d"] = dly["f_cash"].fillna(0) + dly["basis_chg"].fillna(0)
    eq = dly["net_d"].cumsum()
    maxdd_usd = float(-(eq - eq.cummax()).min())
    out = {
        "coverage": round(cov, 5), "n_hours": int(len(panel)),
        "window": [str(panel["date"].iloc[0]), str(panel["date"].iloc[-1])],
        "avg_funding_bp8h": round(float(f6b["funding_rate"].mean()) * 1e4, 4),
        "frac_funding_pos": round(float((f6b["funding_rate"] > 0).mean()), 4),
        "basis_start": round(float(panel["basis"].iloc[0]), 2),
        "basis_end": round(float(panel["basis"].iloc[-1]), 2),
        "basis_mean": round(float(panel["basis"].mean()), 2),
        "funding_cash_usd": round(f_cash, 2),
        "basis_pnl_usd": round(basis_pnl, 2),
        "fees_usd": round(fee_in + fee_out, 2),
        "slip_usd": round(slip, 2),
        "total_pnl_usd_per_btc_pair": round(total, 2),
        "annualized_pct_on_avg_notional": round(ann, 2),
        "maxdd_usd_daily": round(maxdd_usd, 2),
        "elapsed_min": round((time.time() - t0) / 60, 1),
    }
    with open(D9 / "CARRY_SCOUT.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    for k, v in out.items():
        print(f"{k}: {v}", flush=True)


if __name__ == "__main__":
    main()
