"""Phase 6B — funding indirici (FINAL LOCK §5/§8/§9/§11/§24/§25).

- Kaynak (kilitli): Binance USDs-M GET /fapi/v1/fundingRate, BTCUSDT.
- Pencere (kilitli): startTime >= 2020-01-01, endTime <= 2023-06-30T23:59:59Z.
  2023-07+ / 2024 / 2025 ASLA istenmez (assert).
- Sayfalama: limit=1000, startTime = son fundingTime + 1.
- Saklanan: fundingTime + fundingRate SADECE (markPrice ATILIR —
  predicted/intraperiod funding exclusion, lock §5).
- Cikti: data/funding_btcusdt.parquet + MANIFEST_DOWNLOAD_6B.json

Calistir: py -3 scripts/phase6b_download.py
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "experiments" / "phase_06_market_context" / "6B_funding" / "data"
API = "https://fapi.binance.com/fapi/v1/fundingRate"
SYMBOL = "BTCUSDT"  # kilitli
START_MS = int(pd.Timestamp("2020-01-01", tz="UTC").timestamp() * 1000)
END_MS = int(pd.Timestamp("2023-06-30 23:59:59", tz="UTC").timestamp() * 1000)
assert START_MS < END_MS
assert pd.to_datetime(END_MS, unit="ms", utc=True) < pd.Timestamp("2023-07-01", tz="UTC"), \
    "pencere tasmasi"


def fetch_page(start_ms):
    assert START_MS <= start_ms <= END_MS, f"pencere disi istek: {start_ms}"
    url = f"{API}?symbol={SYMBOL}&startTime={start_ms}&endTime={END_MS}&limit=1000"
    req = urllib.request.Request(url, headers={"User-Agent": "zen-genie-6b/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode())
    assert isinstance(payload, list), f"beklenmeyen yanit: {str(payload)[:120]}"
    return payload


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    cursor = START_MS
    pages = 0
    t0 = time.time()
    while True:
        page = fetch_page(cursor)
        pages += 1
        if not page:
            break
        for rec in page:
            # SADECE settled degerler; markPrice bilerek alinmaz
            rows.append((int(rec["fundingTime"]), float(rec["fundingRate"])))
        cursor = max(int(r["fundingTime"]) for r in page) + 1
        print(f"  page {pages}: {len(page)} rows, cursor={cursor}", flush=True)
        if len(page) < 1000:
            break
        time.sleep(0.3)
        if cursor > END_MS:
            break
    df = pd.DataFrame(rows, columns=["funding_ms", "funding_rate"])
    df = df.drop_duplicates("funding_ms").sort_values("funding_ms").reset_index(drop=True)
    # --- integrity + coverage assert'leri ---
    assert len(df) > 0, "STOP: funding verisi bos"
    assert int(df["funding_ms"].iloc[0]) <= START_MS + 8 * 3600 * 1000, \
        f"STOP: ilk settlement pencereden sonra: {df['funding_ms'].iloc[0]}"
    assert not df["funding_ms"].duplicated().any(), "STOP: dup settlement"
    assert df["funding_ms"].is_monotonic_increasing, "STOP: monoton degil"
    assert df["funding_rate"].notna().all(), "STOP: NaN rate"
    assert int(df["funding_ms"].max()) <= END_MS, "STOP: pencere tasmasi"
    # settlement grid: 00/08/16 UTC +-60s tolerans (borsa jitter; ornek:
    # 2020-01-02 08:00:00.002). Tolerans DISI -> STOP. Eksik settlement -> STOP.
    # Kullanimda ACTUAL funding_ms ile asof-backward birlesme yapilir
    # (yuvarlama yok -> 2ms bile ileri sizamaz). Tolerans yalnizca grid
    # aidiyet testidir; implementation disambiguation, RUN_REPORT'ta notlu.
    ts = pd.to_datetime(df["funding_ms"], unit="ms", utc=True)
    grid_ms = (df["funding_ms"].to_numpy() // (8 * 3600 * 1000)) * (8 * 3600 * 1000)
    jit = (df["funding_ms"].to_numpy() - grid_ms) / 1000.0
    assert (np.abs(jit) <= 60).all(), f"STOP: grid disi settlement (max jit {np.abs(jit).max():.1f}s)"
    gaps = df["funding_ms"].diff().dropna().to_numpy() / 1000.0
    assert ((gaps >= 8 * 3600 - 60) & (gaps <= 8 * 3600 + 60)).all(), \
        f"STOP: eksik settlement ({int(((gaps < 8*3600-60)).sum())} adet)"
    print(f"  max jitter: {np.abs(jit).max():.3f}s (ornek: {ts.iloc[np.argmax(np.abs(jit))]})", flush=True)
    df.to_parquet(DATA_DIR / "funding_btcusdt.parquet", index=False)
    manifest = {
        "symbol": SYMBOL, "endpoint": API,
        "window": ["2020-01-01", "2023-06-30"],
        "n_settlements": int(len(df)),
        "first_utc": ts.iloc[0].strftime("%Y-%m-%d %H:%M"),
        "last_utc": ts.iloc[-1].strftime("%Y-%m-%d %H:%M"),
        "pages": pages, "elapsed_s": round(time.time() - t0, 1),
        "markPrice": "EXCLUDED (predicted-funding yasagi)",
        "lock": "M20 6B FINAL",
    }
    with open(DATA_DIR / "MANIFEST_DOWNLOAD_6B.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"TAMAM: {len(df)} settlement ({manifest['first_utc']} -> {manifest['last_utc']})")


if __name__ == "__main__":
    main()
