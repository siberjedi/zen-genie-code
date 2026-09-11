"""Phase 11 PREFLIGHT — lock + mekanik dogrulama (P&L YOK, backtest DEGIL).

Kapsam: 12 CM kontratin deterministik manifesti, tum aylik dosyalarin
indirilmesi (listing->vade), sureklilik/hizalama/settlement-termination
kontrolleri, ters-marjin formul + 10x spike SENTETIK testi, gate
uygulanabilirlik (analitik guc). Getiri/carry/gate-degerlendirme YOK.
Carry P&L, Sharpe, gate SONUCLARI hesaplanmaz (backtest isi).

Kilitli liste (12, degismez): BTCUSD_200925/201225/210326/210625/210924/
211231/220325/220624/220930/221230/230331/230630 (vade: son Cuma 08:00 UTC).

Calistir: py -3 scripts/phase11_preflight.py (arka planda + log)
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
CONTRACTS = [
    ("BTCUSD_200925", "2020-09-25"), ("BTCUSD_201225", "2020-12-25"),
    ("BTCUSD_210326", "2021-03-26"), ("BTCUSD_210625", "2021-06-25"),
    ("BTCUSD_210924", "2021-09-24"), ("BTCUSD_211231", "2021-12-31"),
    ("BTCUSD_220325", "2022-03-25"), ("BTCUSD_220624", "2022-06-24"),
    ("BTCUSD_220930", "2022-09-30"), ("BTCUSD_221230", "2022-12-30"),
    ("BTCUSD_230331", "2023-03-31"), ("BTCUSD_230630", "2023-06-30"),
]
SETTLE_HOUR = 8  # vade Cuma 08:00 UTC (settlement saati)
BASE = "https://data.binance.vision/data/futures/cm/monthly/klines"
MMR = 0.005
K_LOCK = 10.0  # izole teminat: short-notional'in 10 kati (muhendislik marji)


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "zen-genie-p11/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def months_between(y0m0, y1m1):
    y, m = y0m0
    out = []
    while (y, m) <= y1m1:
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def load_month(sym, y, m):
    tag = f"{y}-{m:02d}"
    url = f"{BASE}/{sym}/1h/{sym}-1h-{tag}.zip"
    blob = fetch(url)
    chk = fetch(url + ".CHECKSUM").decode().strip().split()[0]
    assert hashlib.sha256(blob).hexdigest() == chk, f"checksum: {sym} {tag}"
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
    (DATA / "craw").mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "scripts"))
    from phase502_labels import load_dataset_slice
    from src.timeconv import to_ms
    spot = load_dataset_slice()[["date", "close"]]
    ts = pd.to_datetime(spot["date"])
    ts = ts.dt.tz_localize("UTC") if getattr(ts.dt, "tz", None) is None else ts
    sms = to_ms(ts)
    S = spot["close"].to_numpy(float)
    out = {"contracts": {}, "margin_model": {}, "gate_applicability": {}}
    files = []
    for sym, exp in CONTRACTS:
        exp_ts = pd.Timestamp(exp, tz="UTC")
        # listeleme baslangici: kesif manifestinden (yoksa STOP)
        disc = json.load(open(DATA / "quarterly_discovery.json", encoding="utf-8"))
        key = exp  # "YYYY-MM-DD" (discovery ile ayni format)
        first = disc["expiries"][key]["CM"]["months"]
        first = [x["month"] for x in first if x["exists"]][0]
        y0, m0 = int(first[:4]), int(first[5:7])
        ye, me = int(exp[:4]), int(exp[5:7])
        frames = []
        for (yy, mm) in months_between((y0, m0), (ye, me)):
            df, url, chk = load_month(sym, yy, mm)
            frames.append(df)
            files.append({"url": url, "sha256": chk, "rows": len(df)})
        full = pd.concat(frames, ignore_index=True).sort_values("open_ms").reset_index(drop=True)
        assert not full["open_ms"].duplicated().any(), f"STOP dup: {sym}"
        assert (full["close"] > 0).all(), f"STOP non-positive: {sym}"
        full.to_parquet(DATA / "craw" / f"{sym}.parquet", index=False)
        # sureklilik: 1h grid boslugu
        gaps = np.diff(full["open_ms"].to_numpy()) / 3600000.0
        max_gap = float(gaps.max())
        # hizalama (spot +55dk kurali)
        tgt = full["open_ms"].to_numpy() + 55 * 60 * 1000
        pos = np.searchsorted(sms, tgt)
        inb = pos < len(sms)
        ok = np.zeros(len(full), bool)
        ok[inb] = sms[pos[inb]] == tgt[inb]
        P, Sm = full["close"].to_numpy()[ok], S[pos[ok]]
        corr = float(np.corrcoef(np.diff(Sm), np.diff(P))[0, 1]) if ok.sum() > 100 else float("nan")
        # settlement terminasyonu: son bar vade-gunu 08:00 ONCESI mi?
        last_t = pd.to_datetime(full["open_ms"].iloc[-1], unit="ms", utc=True)
        term_ok = bool(last_t <= exp_ts + pd.Timedelta(hours=8))
        out["contracts"][sym] = {
            "expiry": exp, "first_month": first, "n_bars": int(len(full)),
            "max_gap_h": round(max_gap, 2), "align_n": int(ok.sum()),
            "align_corr_diff": round(corr, 5),
            "last_bar": str(last_t), "termination_clean": term_ok,
        }
        print(f"{sym}: bar={len(full)} maxgap={max_gap:.1f}h align={corr:.4f} "
              f"son={last_t} term_ok={term_ok}", flush=True)
    # ters-marjin SENTETIK dogrulama (gercek P&L DEGIL): 10x sokaga k karsiligi
    # model: balance = W0 + (p0-P)/p0*notional_btc... birim: BTC-bazinda short 1 BTC,
    # W0 = k BTC (k x notional, notional=1 BTC) ; oran = balance/notional_btc_degeri
    # sadelik: fiyat p, giris p0=1 normalize -> balance = k - (p-1), oran = balance/p
    out["margin_model"]["spec"] = ("izole, W0=k BTC, MMR %0.5, breach->likidasyon, "
                                   "kurtarma YOK; k=1000% muhendislik marji (10x tampon)")
    for mult in (2.0, 5.0, 9.58, 10.0):
        bal = K_LOCK - (mult - 1.0)
        out["margin_model"][f"spike_{mult}x"] = {
            "balance_btc": round(bal, 3), "ratio": round(bal / mult, 4),
            "survives": bool(bal / mult > MMR)}
        print(f"  sentetik {mult}x: balance={bal:.2f}BTC oran={bal/mult:.4f} "
              f"-> {'sagkalir' if bal/mult > MMR else 'OLUR'}", flush=True)
    # gate uygulanabilirlik (analitik; veri-gucu degil, yapi)
    from statsmodels.stats.power import TTestPower
    pw = TTestPower()
    for dd, tag in ((0.30, "d030"), (0.80, "d080")):
        pwr = float(pw.power(effect_size=dd, nobs=12, alpha=0.05, alternative="larger"))
        out["gate_applicability"][tag] = round(pwr, 4)
    print(f"  guc n=12: d=0.30 -> {out['gate_applicability']['d030']}, "
          f"d=0.80 -> {out['gate_applicability']['d080']}", flush=True)
    out["n_files"] = len(files)
    with open(DATA / "PREFLIGHT11.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    with open(DATA / "MANIFEST_CM_P11.json", "w", encoding="utf-8") as f:
        json.dump({"n_files": len(files), "files": files}, f, indent=2)
    print(f"YAZILDI: PREFLIGHT11.json ({len(files)} dosya)", flush=True)


if __name__ == "__main__":
    main()
