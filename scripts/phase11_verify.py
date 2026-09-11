"""Phase 11 SCOUT-2 — secili quarterly dosyalari indir + convergence/hizalama/sureklilik.

Dosyalar (kilitli pencere ici, 2020-2023H1):
 CM: BTCUSD_200925/2020-06 (ilk), BTCUSD_210326/2021-03 (vade),
     BTCUSD_221230/2022-12 (vade), BTCUSD_230630/2023-06 (vade)
 UM: BTCUSDT_210625/2021-03 (ilk-tam), BTCUSDT_221230/2022-12 (vade),
     BTCUSDT_230630/2023-06 (vade)
Kontroller: checksum, grid-hizalama (spot +55dk kurali, corr>0.99),
 sureklilik (gap taramasi), vade-son-bar basis ~0 (yakinsama).
Carry P&L HESAPLANMAZ (scout disi).
Cikti: data/verify_quarterly.json (+ ham parquet'ler data/qraw/)
Calistir: py -3 scripts/phase11_verify.py
"""
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

DATA = ROOT / "experiments" / "phase_11_basis" / "data"
FILES = [
    ("CM", "BTCUSD_200925", "2020-06"), ("CM", "BTCUSD_210326", "2021-03"),
    ("CM", "BTCUSD_221230", "2022-12"), ("CM", "BTCUSD_230630", "2023-06"),
    ("UM", "BTCUSDT_210625", "2021-03"), ("UM", "BTCUSDT_221230", "2022-12"),
    ("UM", "BTCUSDT_230630", "2023-06"),
]
BASE = {"CM": "data/futures/cm/monthly/klines", "UM": "data/futures/um/monthly/klines"}


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "zen-genie-p11/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def load_month(venue, sym, ym):
    url = f"https://data.binance.vision/{BASE[venue]}/{sym}/1h/{sym}-1h-{ym}.zip"
    blob = fetch(url)
    chk = fetch(url + ".CHECKSUM").decode().strip().split()[0]
    assert hashlib.sha256(blob).hexdigest() == chk, f"checksum: {sym} {ym}"
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
    return pd.DataFrame({"open_ms": ot.to_numpy(), "close": cl.to_numpy()}), url, chk


def main():
    (DATA / "qraw").mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "scripts"))
    from phase502_labels import load_dataset_slice
    from src.timeconv import to_ms
    spot = load_dataset_slice()[["date", "close"]]
    ts = pd.to_datetime(spot["date"])
    ts = ts.dt.tz_localize("UTC") if getattr(ts.dt, "tz", None) is None else ts
    sms = to_ms(ts)
    S = spot["close"].to_numpy(float)
    out = {}
    for venue, sym, ym in FILES:
        df, url, chk = load_month(venue, sym, ym)
        df.to_parquet(DATA / "qraw" / f"{sym}_{ym}.parquet", index=False)
        tgt = df["open_ms"].to_numpy() + 55 * 60 * 1000
        pos = np.searchsorted(sms, tgt)
        inb = pos < len(sms)
        ok = np.zeros(len(df), bool)
        ok[inb] = sms[pos[inb]] == tgt[inb]
        P, Sm = df["close"].to_numpy()[ok], S[pos[ok]]
        corr = float(np.corrcoef(np.diff(Sm), np.diff(P))[0, 1])
        # gap taramasi (1h grid): beklenen vs mevcut
        exp_bars = (df["open_ms"].iloc[-1] - df["open_ms"].iloc[0]) // 3600000 + 1
        rec = {"url": url, "sha256": chk, "n_bars": int(len(df)),
               "first": str(pd.to_datetime(df["open_ms"].iloc[0], unit="ms", utc=True)),
               "last": str(pd.to_datetime(df["open_ms"].iloc[-1], unit="ms", utc=True)),
               "expected_bars": int(exp_bars), "missing_bars": int(exp_bars - len(df)),
               "align_n": int(ok.sum()), "align_corr_diff": round(corr, 5),
               "last_basis": round(float(P[-1] - Sm[-1]), 2) if ok.sum() else None,
               "last_basis_bps": round(float((P[-1] - Sm[-1]) / Sm[-1] * 1e4), 2) if ok.sum() else None}
        out[f"{sym}/{ym}"] = rec
        print(f"{sym} {ym}: n={rec['n_bars']}/{rec['expected_bars']} "
              f"align_corr={corr:.4f} last_basis={rec['last_basis']} "
              f"({rec['last_basis_bps']}bp)", flush=True)
    with open(DATA / "verify_quarterly.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("YAZILDI: verify_quarterly.json")


if __name__ == "__main__":
    main()
