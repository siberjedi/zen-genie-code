"""Phase 14 MICRO-HORIZON PILOT — aggTrades toxicity/decay (TANIMLAYICI).

PILOT AYI (kilitli, indirme-oncesi): 2023-02 (BTCUSDT spot).
Secim kurali: pencere-ici (2020-01..2023-06) son sakin TAM ay; olay-aylari
dislandi (liste asagida, kamusal piyasa-tarihinden; sinyal verisi GORULMEDI):
  Mar-2020 (cokus), May-2021 (deleveraging), Kas-2021 (tepe),
  May-2022 (Luna), Kas-2022 (FTX), Haz-2023 (ETF-spike + pencere-kenari).
Bu kural yon-notr'dur (sinyal-gucune gore secim YOK).

Kapsam: TEK ay, TEK coin (BTCUSDT spot), futures YOK, yeni feature YOK,
model YOK, threshold-opt YOK, gate/FDR/p-degeri YOK, holdout YOK.
Sinyal (sabit): 60sn trailing signed-notional + volume-normalize imbalance;
siralama: normalize imbalance; 5 quantile (sabit); ufuklar 1/10/60/300sn.
Leakage: yalnizca (t-60sn, t] penceresi; forward t-sonrasi; future-normalizasyon YOK.
Quantile kesikleri betimsel-havuzlamadir (secim YOK).

Calistir: py -3 scripts/phase14_pilot.py (arka planda + log)
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
P14 = ROOT / "experiments" / "phase_14"
DATAP14 = P14 / "data_pilot"
PILOT_TAG = "2023-02"
PILOT_URL = ("https://data.binance.vision/data/spot/monthly/aggTrades/"
             "BTCUSDT/BTCUSDT-aggTrades-2023-02.zip")
SIG_W = 60
HORIZONS = [1, 10, 60, 300]
N_Q = 5


def fetch(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "zen-genie-p14/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main():
    DATAP14.mkdir(parents=True, exist_ok=True)
    print(f"== P14 PILOT ({PILOT_TAG}, BTCUSDT spot) ==", flush=True)
    # 1. indir + checksum
    blob = fetch(PILOT_URL)
    chk = fetch(PILOT_URL + ".CHECKSUM").decode().strip().split()[0]
    assert hashlib.sha256(blob).hexdigest() == chk, "STOP: checksum"
    print(f"  indirildi: {len(blob)/1e9:.2f} GB, sha256 OK", flush=True)
    zf = zipfile.ZipFile(io.BytesIO(blob))
    names = [n for n in zf.namelist() if n.endswith(".csv")]
    assert len(names) == 1
    # 2. kolon tespiti (header'li/headersiz)
    with zf.open(names[0]) as fh:
        head = fh.read(4096).decode()
    first_line = head.splitlines()[0]
    has_header = first_line.strip().lower().startswith("aggregate")
    print(f"  header: {has_header}; ilk satir: {first_line[:110]}", flush=True)
    # 3. chunk-okuma -> saniye-parcallari (bellek-sinirli).
    # ibm normalizasyonu: 'true'/'false'/True/False hepsi kabul; disi maskeli.
    partials = []
    n_rows = 0
    rdr = pd.read_csv(zf.open(names[0]),
                      header=0 if has_header else None, chunksize=2_000_000,
                      usecols=[0, 1, 2, 3, 4, 5, 6])
    qc = {"n_rows": 0, "ts_nonmono": 0, "gap_over_60s": 0,
          "price_le0": 0, "qty_le0": 0, "nan": 0, "ibm_vals": set(),
          "last_le_first_viol": 0}
    prev_last_ts = None
    for ch in rdr:
        ch.columns = ["agg_id", "price", "qty", "first_id", "last_id", "ts", "ibm"]
        n_rows += len(ch)
        qc["n_rows"] = n_rows
        qc["nan"] += int(ch.isna().sum().sum())
        qc["price_le0"] += int((ch["price"] <= 0).sum())
        qc["qty_le0"] += int((ch["qty"] <= 0).sum())
        ibm_norm = ch["ibm"].astype(str).str.strip().str.lower().map(
            {"true": True, "false": False})
        qc["ibm_vals"] |= set(ibm_norm.dropna().unique().tolist())
        qc["last_le_first_viol"] += int((ch["last_id"] < ch["first_id"]).sum())
        ts = ch["ts"].to_numpy(dtype="int64")
        if prev_last_ts is not None and ts[0] < prev_last_ts:
            qc["ts_nonmono"] += 1
        d = np.diff(ts)
        qc["gap_over_60s"] += int((d[d > 0] > 60000).sum())
        if (d < 0).any():
            qc["ts_nonmono"] += int((d < 0).sum())
        prev_last_ts = ts[-1]
        sign = np.where(ch["ibm"].to_numpy() == False, 1.0, -1.0)  # noqa: E712
        # True->aggressive SELL(-1); False->aggressive BUY(+1); baska deger->NaN maskesi
        mask_known = ch["ibm"].isin([True, False]).to_numpy()
        signed = ch["price"].to_numpy(float) * ch["qty"].to_numpy(float) * sign
        signed[~mask_known] = 0.0
        vol = (ch["price"].to_numpy(float) * ch["qty"].to_numpy(float))
        vol[~mask_known] = 0.0
        sec = (ts // 1000).astype("int64")
        g = pd.DataFrame({"sec": sec, "signed": signed, "vol": vol,
                          "px": ch["price"].to_numpy(float), "ts": ts})
        agg = g.groupby("sec").agg(signed=("signed", "sum"), vol=("vol", "sum"),
                                   px=("px", "last"), ts=("ts", "max"),
                                   n=("px", "size"))
        partials.append(agg)
        print(f"  chunk: {n_rows/1e6:.1f}M satir", flush=True)
    qc["ibm_vals"] = sorted([str(x) for x in qc["ibm_vals"]])
    qcdf = pd.concat(partials)
    bars = qcdf.groupby(level=0).agg(signed=("signed", "sum"), vol=("vol", "sum"),
                                     px=("px", "last"), n=("n", "sum"))
    bars = bars.sort_index()
    print(f"  saniye-bar: {len(bars)} | satir: {qc['n_rows']}", flush=True)
    with open(DATAP14 / "pilot_qc.json", "w", encoding="utf-8") as f:
        json.dump({k: (v if not isinstance(v, (np.integer,)) else int(v))
                   for k, v in qc.items()}, f, indent=2, default=str)
    # kritik QC gate'leri (STOP/ISSUE): monotonluk + pozitiflik + ibm degerleri
    issues = []
    if qc["price_le0"] or qc["qty_le0"]:
        issues.append("price/qty<=0 mevcut")
    if set(qc["ibm_vals"]) - {"True", "False"}:
        issues.append(f"beklenmeyen ibm: {qc['ibm_vals']}")
    if qc["ts_nonmono"] > len(bars) * 0.001:
        issues.append("asiri non-monoton ts")
    # 4. tam saniye gridi (ffill fiyat; hacim 0-doldur)
    t0 = int(bars.index.min())
    full_idx = np.arange(t0, int(bars.index.max()) + 1, dtype="int64")
    px = pd.Series(bars["px"].to_numpy(), index=bars.index).reindex(full_idx).ffill()
    ok_hist = px.notna()
    first_valid = int(np.where(ok_hist.to_numpy())[0][0])
    px = px.iloc[first_valid:]
    full_idx = full_idx[first_valid:]
    vol = pd.Series(bars["vol"].to_numpy(), index=bars.index).reindex(full_idx).fillna(0.0)
    sgn = pd.Series(bars["signed"].to_numpy(), index=bars.index).reindex(full_idx).fillna(0.0)
    ffill_frac = 1.0 - len(bars) / len(full_idx)
    # 5. sinyal (60sn trailing; nedensel) + forward getiriler
    pxv = px.to_numpy(float)
    sv = sgn.rolling(SIG_W, min_periods=SIG_W).sum().to_numpy()
    vv = vol.rolling(SIG_W, min_periods=SIG_W).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        imb = np.where(vv > 0, sv / vv, np.nan)
    res = {"month": PILOT_TAG, "n_seconds": int(len(full_idx)),
           "ffill_frac": round(float(ffill_frac), 5),
           "n_trades": int(qc["n_rows"]), "issues": issues, "horizons": {}}
    for h in HORIZONS:
        yh = np.full(len(pxv), np.nan)
        yh[:-h] = pxv[h:] / pxv[:-h] - 1.0
        m = ~np.isnan(imb) & ~np.isnan(yh)
        q = pd.qcut(pd.Series(imb[m]), N_Q, labels=False, duplicates="drop")
        qt = {}
        for qi in range(N_Q):
            mm = (q.to_numpy() == qi)
            if mm.sum() == 0:
                continue
            yy = yh[m][mm] * 1e4  # bp
            qt[f"Q{qi+1}"] = {"n": int(mm.sum()),
                              "mean_bp": round(float(yy.mean()), 4),
                              "median_bp": round(float(np.median(yy)), 4),
                              "std_bp": round(float(yy.std(ddof=1)), 4),
                              "hit_rate": round(float((yy > 0).mean()), 4)}
        means = [qt[f"Q{i+1}"]["mean_bp"] for i in range(N_Q) if f"Q{i+1}" in qt]
        from scipy.stats import spearmanr
        rho = float(spearmanr(range(1, len(means) + 1), means)[0]) if len(means) == N_Q else float("nan")
        q5, q1 = means[-1], means[0]
        res["horizons"][str(h)] = {"n": int(m.sum()), "quantiles": qt,
                                   "gross_effect_bp": round(q5 - q1, 4),
                                   "spearman_rho": round(rho, 4)}
        print(f"  h={h}s: n={m.sum()} gross(Q5-Q1)={q5-q1:+.3f}bp rho={rho:+.3f}", flush=True)
    with open(DATAP14 / "pilot_decay.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    # 6. grafik (opsiyonel; yoksa tablo-yeterli notu)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        hs = sorted(int(k) for k in res["horizons"])
        eff = [res["horizons"][str(h)]["gross_effect_bp"] for h in hs]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot([str(h) + "s" for h in hs], eff, marker="o")
        for c in (30, 10, 5, 1):
            ax.axhline(c, linestyle="--", linewidth=0.8)
            ax.axhline(-c, linestyle="--", linewidth=0.8)
        ax.set_title("P14 decay: Q5-Q1 gross (bp) — cost ref 30/10/5/1bp (sadece referans)")
        ax.set_ylabel("bp")
        fig.tight_layout()
        fig.savefig(DATAP14 / "decay_curve.png", dpi=110)
        res["chart"] = "decay_curve.png"
        with open(DATAP14 / "pilot_decay.json", "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        print("  grafik: decay_curve.png", flush=True)
    except Exception as e:
        print(f"  grafik atlandi ({type(e).__name__}); tablo yeterli", flush=True)
    print("TAMAM", flush=True)


if __name__ == "__main__":
    main()
