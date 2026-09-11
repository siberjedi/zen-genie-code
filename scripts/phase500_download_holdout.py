"""Phase 5 — FINAL_TEST_P5 (2025H1) holdout indirme + integrity (Bing REST API).

Kapsam: YALNIZCA 2025-01-01 00:00 UTC -> 2025-06-30 23:55 UTC (5m klines).
- Mevcut 2020-2023 feather dataset'ine DOKUNMAZ.
- Final Test B (2024H1) / C (2024H2) verisine ERİŞMEZ.
- NO TRAINING / NO TUNING / NO SELECTION / NO EVALUATION.
"""
import json
import urllib.request
import hashlib
import time
import pandas as pd

PAIR = "BTC/USDT"
SYMBOL = "BTCUSDT"
TF_MS = 5 * 60 * 1000
START_MS = 1735689600000  # 2025-01-01 00:00 UTC
END_MS = 1751328000000    # 2025-07-01 00:00 UTC (exclusive)
EXPECTED = 52128          # 2025H1 5m mum sayısı (dolu pencere)

OUT = r"experiments/phase_05_ml/holdout/BTC_USDT-5m_2025H1.feather"


def fetch_all():
    rows = []
    cursor = START_MS
    while cursor < END_MS:
        url = (f"https://api.binance.com/api/v3/klines?"
               f"symbol={SYMBOL}&interval=5m&startTime={cursor}"
               f"&endTime={END_MS - 1}&limit=1000")
        with urllib.request.urlopen(url, timeout=30) as r:
            batch = json.load(r)
        if not batch:
            break
        rows.extend(batch)
        cursor = batch[-1][0] + TF_MS
        if len(batch) < 1000:
            # son partition: endTime'e kadar geldik
            break
        time.sleep(0.12)  # rate-limit nezaketi
    return rows


def main():
    rows = fetch_all()
    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "trades", "taker_buy_base", "taker_buy_quote", "ignore"])
    df["date"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    # mevcut schema ile birebir: date, open, high, low, close, volume
    out = pd.DataFrame({
        "date": df["date"],
        "open": df["open"].astype(float),
        "high": df["high"].astype(float),
        "low": df["low"].astype(float),
        "close": df["close"].astype(float),
        "volume": df["volume"].astype(float),
    })
    # sort + dup kontrol
    out = out.sort_values("date").reset_index(drop=True)
    dup = out["date"].duplicated().sum()
    # 5m grid kontrolü (govde)
    grid = pd.date_range(start=pd.Timestamp(START_MS, unit="ms", tz="UTC"),
                         end=pd.Timestamp(END_MS, unit="ms", tz="UTC") - pd.Timedelta(minutes=5),
                         freq="5min")
    present = set(out["date"])
    missing = [str(x) for x in grid if x not in present]
    # tamamlanmamış son bar kontrolü: close_time + 1 == open_time
    # (klines close_time, bir sonraki mumun açılışı eksildir)
    print("rows_downloaded", len(out))
    print("date_first", out["date"].iloc[0])
    print("date_last", out["date"].iloc[-1])
    print("duplicates", dup)
    print("nulls", int(out.isna().sum().sum()))
    print("missing_intervals", len(missing))
    if len(missing):
        print("missing_sample", missing[:10])
    print("ohlc_positivity", int((out[["high", "low", "close"]].le(0)).sum().sum()))

    # integrity: high >= max(open,close,low), low <= min(open,close)
    bad_ohlc = int((
        (out["high"] < out[["open", "close", "low"]].max(axis=1)) |
        (out["low"] > out[["open", "close", "high"]].min(axis=1))
    ).sum())
    print("bad_ohlc", bad_ohlc)

    out.to_feather(OUT)
    with open(OUT, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
    print("sha256", h)
    print("file", OUT)
    # manifest yaz
    manifest = {
        "symbol": PAIR,
        "timeframe": "5m",
        "reservation": "FINAL_TEST_P5",
        "window": "2025-01-01 00:00 UTC -> 2025-06-30 23:55 UTC",
        "expected_rows": int(EXPECTED),
        "rows": int(len(out)),
        "duplicates": int(dup),
        "nulls": int(out.isna().sum().sum()),
        "missing_intervals": int(len(missing)),
        "missing_sample": missing[:10],
        "ohlc_positivity_violations": int((out[["high", "low", "close"]].le(0)).sum().sum()),
        "ohlc_relationship_violations": bad_ohlc,
        "date_first": str(out["date"].iloc[0]),
        "date_last": str(out["date"].iloc[-1]),
        "sha256": h,
        "schema": ["date", "open", "high", "low", "close", "volume"],
        "integrity_pass": (len(out) == EXPECTED) and (dup == 0)
                          and (int(out.isna().sum().sum()) == 0)
                          and (len(missing) == 0) and (bad_ohlc == 0),
    }
    out_dir = OUT.rsplit("/", 1)[0]
    with open(out_dir + "/manifest_2025H1.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print("integrity_pass", manifest["integrity_pass"])


if __name__ == "__main__":
    main()