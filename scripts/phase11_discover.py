"""Phase 11 SCOUT — quarterly kesif (HEAD taramasi, indirme YOK).

14 ceyrek (2020Q1-2023Q2) x 2 venue (CM BTCUSD_YYMMDD / UM BTCUSDT_YYMMDD)
x vade-oncesi 12 ay: dosya varligi cikarilir.
Cikti: data/quarterly_discovery.json
Calistir: py -3 scripts/phase11_discover.py
"""
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments" / "phase_11_basis" / "data"

EXPIRIES = [(2020, 3, 27), (2020, 6, 26), (2020, 9, 25), (2020, 12, 25),
            (2021, 3, 26), (2021, 6, 25), (2021, 9, 24), (2021, 12, 31),
            (2022, 3, 25), (2022, 6, 24), (2022, 9, 30), (2022, 12, 30),
            (2023, 3, 31), (2023, 6, 30)]
VENUES = {"CM": ("data/futures/cm/monthly/klines", "BTCUSD_"),
          "UM": ("data/futures/um/monthly/klines", "BTCUSDT_")}


def probe(url):
    req = urllib.request.Request(url, headers={"User-Agent": "zen-genie-p11/1.0"},
                                 method="HEAD")
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return (r.status == 200, r.headers.get("Content-Length"))
    except Exception:
        return (False, None)


def months_back(y, m, n=12):
    out = []
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return sorted(out)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    res = {}
    for (y, m, d) in EXPIRIES:
        tag = f"{y}-{m:02d}-{d:02d}"
        sym = f"{str(y)[2:]}{m:02d}{d:02d}"
        res[tag] = {}
        for v, (base, pre) in VENUES.items():
            have = []
            for (yy, mm) in months_back(y, m):
                url = (f"https://data.binance.vision/{base}/{pre}{sym}/1h/"
                       f"{pre}{sym}-1h-{yy}-{mm:02d}.zip")
                ok, size = probe(url)
                have.append({"month": f"{yy}-{mm:02d}", "exists": ok,
                             "bytes": size})
            res[tag][v] = {"symbol": pre + sym, "months": have}
        print(f"{tag}: CM={sum(1 for x in res[tag]['CM']['months'] if x['exists'])} "
              f"UM={sum(1 for x in res[tag]['UM']['months'] if x['exists'])}", flush=True)
    with open(DATA / "quarterly_discovery.json", "w", encoding="utf-8") as f:
        json.dump({"expiries": res}, f, indent=2)
    print("YAZILDI: quarterly_discovery.json")


if __name__ == "__main__":
    main()
