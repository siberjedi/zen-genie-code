"""Phase 6C — OI indirici (FINAL LOCK §5/§8/§9/§11/§13/§25).

- Kaynak (kilitli): data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/
  {SYM}-metrics-YYYY-MM-DD.zip ; gunluk dosyalar, 2020-01-01..2023-06-30.
  2023-07+ / 2024 / 2025 tarihi URETILMEZ (assert).
- Kolonlar (kilitli): create_time + sum_open_interest SADECE
  (value/oran kolonlari parse edilmez).
- Dedup (kilitli §9): gun-sirasi birlestir, create_time sirala,
  drop_duplicates(keep='first'); kalan dup -> STOP.
- Coverage gate: ilk OI tarihi > 2020-09-30 -> STOP.
- Cikti: data/oi_btcusdt.parquet (create_ms, oi) + MANIFEST_DOWNLOAD_6C.json

Calistir: py -3 scripts/phase6c_download.py
"""
import hashlib
import io
import json
import sys
import time
import urllib.request
import zipfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.timeconv import to_ms

DATA_DIR = ROOT / "experiments" / "phase_06_market_context" / "6C_oi" / "data"
BASE_URL = "https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT"
SYM = "BTCUSDT"  # kilitli
FIRST_DAY = date(2020, 1, 1)
LAST_DAY = date(2023, 6, 30)  # KILIT: sonrasi ASLA
FIRST_OI_LIMIT = pd.Timestamp("2020-09-30", tz="UTC")


def day_range():
    d = FIRST_DAY
    out = []
    while d <= LAST_DAY:
        out.append(d)
        d += timedelta(days=1)
    return out


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "zen-genie-6c/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    days = day_range()
    print(f"gun={len(days)} dosya", flush=True)
    frames = []
    manifest_files = []
    missing_days = []
    t0 = time.time()
    for d in days:
        tag = d.strftime("%Y-%m-%d")
        assert d <= LAST_DAY, f"pencere disi: {tag}"
        url = f"{BASE_URL}/{SYM}-metrics-{tag}.zip"
        try:
            blob = fetch(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Erken-donem dosya yoklugu BEKLENIR (kapsama ~2020-09);
                # kaydedilir, run asamasinda gate'lenir (VAL boslugu -> STOP).
                missing_days.append(tag)
                continue
            raise RuntimeError(f"STOP indirme hatasi: {tag}: HTTP {e.code}")
        except Exception as e:
            raise RuntimeError(f"STOP indirme hatasi: {tag}: "
                               f"{type(e).__name__} {e}")
        try:
            chk_expect = fetch(url + ".CHECKSUM").decode().strip().split()[0]
        except Exception as e:
            raise RuntimeError(f"STOP checksum alinamadi: {tag}: {e}")
        if hashlib.sha256(blob).hexdigest() != chk_expect:
            raise RuntimeError(f"STOP checksum uyumsuz: {tag}")
        zf = zipfile.ZipFile(io.BytesIO(blob))
        names = [n for n in zf.namelist() if n.endswith(".csv")]
        assert len(names) == 1, f"beklenmeyen icerik: {tag} {names}"
        df = pd.read_csv(io.BytesIO(zf.read(names[0])), usecols=["create_time", "sum_open_interest"])
        ts = pd.to_datetime(df["create_time"])
        if getattr(ts.dt, "tz", None) is None:
            ts = ts.dt.tz_localize("UTC")
        oi = df["sum_open_interest"].astype(float)
        # R-QC (revizyon): OI <= 0 VEYA non-finite => invalid => missing (NaN).
        # Venue-side sifir-OI glitch (ornek: 2021-05-22 04:25-05:10, 10 snapshot).
        # DOLDURMA YOK. Dropna politikasi split'te dusurur.
        bad = ~(oi > 0) | (~np.isfinite(oi.to_numpy()))
        n_bad = int(np.asarray(bad).sum())
        if n_bad:
            print(f"  UYARI {tag}: {n_bad} invalid-OI snapshot -> NaN (drop)", flush=True)
        oi = oi.where(~pd.Series(bad, index=oi.index), np.nan)
        frames.append(pd.DataFrame({"create_ms": to_ms(ts),
                                    "oi": oi.to_numpy(), "src_day": tag}))
        manifest_files.append({"url": url, "sha256": chk_expect,
                               "bytes": len(blob), "rows": len(df)})
        if len(manifest_files) % 200 == 0:
            print(f"  {len(manifest_files)}/{len(days)} OK", flush=True)
        time.sleep(0.15)
    full = pd.concat(frames, ignore_index=True)
    full = full.sort_values(["src_day", "create_ms"]).reset_index(drop=True)
    # kilitli dedup: erken-gun dosyasi kazanir
    full = full.drop_duplicates(subset="create_ms", keep="first").reset_index(drop=True)
    assert not full["create_ms"].duplicated().any(), "STOP: dedup sonrasi dup"
    full = full.sort_values("create_ms").reset_index(drop=True)
    assert full["create_ms"].is_monotonic_increasing, "STOP: monoton degil"
    first_utc = pd.to_datetime(full["create_ms"].iloc[0], unit="ms", utc=True)
    last_utc = pd.to_datetime(full["create_ms"].iloc[-1], unit="ms", utc=True)
    if first_utc > FIRST_OI_LIMIT:
        raise RuntimeError(f"STOP: ilk OI {first_utc} > 2020-09-30")
    full[["create_ms", "oi"]].to_parquet(DATA_DIR / "oi_btcusdt.parquet", index=False)
    n_nan = int(full["oi"].isna().sum())
    print(f"  toplam NaN snapshot (drop): {n_nan}", flush=True)
    manifest = {"symbol": SYM, "source": BASE_URL, "n_days": len(days),
                "n_files": len(manifest_files), "n_missing_days": len(missing_days),
                "missing_days": missing_days,                 "n_snapshots": int(len(full)),
                "n_nan_snapshots_dropped": n_nan,
                "zero_oi_policy": "NaN-then-drop (no fill)",
                "first_utc": first_utc.strftime("%Y-%m-%d %H:%M"),
                "last_utc": last_utc.strftime("%Y-%m-%d %H:%M"),
                "dedup_rule": "gun-sirasi + keep-first",
                "elapsed_s": round(time.time() - t0, 1),
                "files": manifest_files, "lock": "M20 6C FINAL"}
    with open(DATA_DIR / "MANIFEST_DOWNLOAD_6C.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"TAMAM: {len(full)} snapshot ({manifest['first_utc']} -> {manifest['last_utc']})")


if __name__ == "__main__":
    main()
