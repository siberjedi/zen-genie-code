"""Phase 6A — cross-asset 5m kline indirici (FINAL LOCK §5/§8/§11/§24/§25).

- Universe (kilitli): ETHUSDT BNBUSDT XRPUSDT ADAUSDT DOGEUSDT LTCUSDT BCHUSDT
- Pencereler (kilitli): SADECE 2020-01 .. 2023-06 aylik dosyalari.
  2023-07+ / 2024 / 2025 URL'si URETILMEZ (assert ile yasakli).
- Kaynak: https://data.binance.vision/data/spot/monthly/klines/{sym}/5m/
- Dogrulama: her zip icin .CHECKSUM karsilastirmasi (SHA256).
- Cikti: data/xa_{SYM}.parquet (open_ms, close float) + MANIFEST_DOWNLOAD_6A.json
- BTC feather'a DOKUNULMAZ; protected pencereler yuklenmez/indirilemez.

Calistir: py -3 scripts/phase6a_download.py
"""
import hashlib
import io
import json
import sys
import time
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "experiments" / "phase_06_market_context" / "6A_cross_asset" / "data"
BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"
UNIVERSE = ["ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT", "BCHUSDT"]
FIRST_MONTH = (2020, 1)
LAST_MONTH = (2023, 6)  # KILIT: 2023-06 sonrasi ASLA
BANNED_YEARS = ("2024", "2025", "2026", "2027")


def month_range():
    y, m = FIRST_MONTH
    out = []
    while (y, m) <= LAST_MONTH:
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def build_url(sym, y, m):
    assert str(y) not in BANNED_YEARS, f"YASAK YIL: {y}"
    assert (y, m) <= LAST_MONTH, f"pencere disi: {y}-{m:02d}"
    assert sym in UNIVERSE, f"universe disi: {sym}"
    return f"{BASE_URL}/{sym}/5m/{sym}-5m-{y}-{m:02d}.zip"


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "zen-genie-6a/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    months = month_range()
    print(f"universe={len(UNIVERSE)} ay={len(months)} dosya={len(UNIVERSE)*len(months)}", flush=True)
    manifest = {"universe": UNIVERSE, "first_month": "2020-01", "last_month": "2023-06",
                "files": [], "symbols": {}}
    t0 = time.time()
    for sym in UNIVERSE:
        frames = []
        for (y, m) in months:
            url = build_url(sym, y, m)
            tag = f"{sym} {y}-{m:02d}"
            try:
                blob = fetch(url)
            except Exception as e:
                raise RuntimeError(f"STOP coverage problemi: {tag}: {type(e).__name__} {e}")
            # checksum
            try:
                chk_raw = fetch(url + ".CHECKSUM").decode().strip()
                chk_expect = chk_raw.split()[0]
            except Exception as e:
                raise RuntimeError(f"STOP checksum alinamadi: {tag}: {e}")
            chk_got = hashlib.sha256(blob).hexdigest()
            if chk_got != chk_expect:
                raise RuntimeError(f"STOP checksum uyumsuz: {tag}")
            zf = zipfile.ZipFile(io.BytesIO(blob))
            names = [n for n in zf.namelist() if n.endswith(".csv")]
            assert len(names) == 1, f"beklenmeyen zip icerigi: {tag} {names}"
            df = pd.read_csv(io.BytesIO(zf.read(names[0])), header=None)
            # kolonlar: open_time open high low close volume close_time qav ntrades tbb tbq ignore
            sub = pd.DataFrame({"open_ms": df[0].astype("int64"),
                                "close": df[4].astype(float)})
            frames.append(sub)
            manifest["files"].append({"url": url, "sha256": chk_got,
                                      "bytes": len(blob), "rows": len(sub)})
            print(f"  OK {tag} rows={len(sub)}", flush=True)
        full = pd.concat(frames, ignore_index=True).sort_values("open_ms").reset_index(drop=True)
        # integrity: monoton + dup yok
        assert full["open_ms"].is_monotonic_increasing, f"monoton degil: {sym}"
        assert not full["open_ms"].duplicated().any(), f"dup bar: {sym}"
        assert (full["close"] > 0).all(), f"non-positive close: {sym}"
        # coverage: ilk/son bar raporu (kesintisizlik orani ayri kontrollerde)
        manifest["symbols"][sym] = {
            "n_bars": int(len(full)),
            "first_ms": int(full["open_ms"].iloc[0]),
            "last_ms": int(full["open_ms"].iloc[-1]),
            "first_utc": pd.to_datetime(full["open_ms"].iloc[0], unit="ms", utc=True).strftime("%Y-%m-%d %H:%M"),
            "last_utc": pd.to_datetime(full["open_ms"].iloc[-1], unit="ms", utc=True).strftime("%Y-%m-%d %H:%M"),
        }
        full.to_parquet(DATA_DIR / f"xa_{sym}.parquet", index=False)
        print(f"DONE {sym}: {len(full)} bar", flush=True)
    manifest["elapsed_s"] = round(time.time() - t0, 1)
    manifest["lock"] = "M20 6A FINAL: 2020-01..2023-06 only; no 2023-07+"
    with open(DATA_DIR / "MANIFEST_DOWNLOAD_6A.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"TAMAM: {len(manifest['files'])} dosya, {manifest['elapsed_s']}s")


if __name__ == "__main__":
    main()
