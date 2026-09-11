"""Phase 10 PREFLIGHT — kural dondurma + makine dogrulama (GETIRI YOK).

Kapsam: 3 kuralin event takvimi (SADECE takvim; fiyat YUKLENMEZ — date kolonu
haric), overlap kurallari, coverage, guc on-hesabi, settlement capraz-kontrol,
FDR-3/metik/gate spec kilidi. Getiri/P&L/Sharpe/gate-degerlendirme YOK
(onlar backtest).
Kurallar (frozen, degismez):
 E1 weekend-long: Cuma 23:55 giris -> Pazar 23:55 flat.
 E2 overnight-long: her gun 00:00 -> 08:00 UTC.
 E3 post-settlement-fade short: T -> T+3h (T in {00,08,16} UTC).
Overlap kurali (kilitli): kurallar BAGIMSIZ portfoyler (capraz-netting YOK);
 kural-ici max-concurrent==1 assert'li; capraz-overlap orani betimsel.
Cikis bari yoksa event DUSER (deterministik; raporlu).

Calistir: py -3 scripts/phase10_preflight.py
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase502_labels import load_dataset_slice
from src.freqai.p5_splits import TRAIN_START, VAL_END
from src.timeconv import to_ms

D10 = ROOT / "experiments" / "phase_10_calendar" / "data"
T0 = pd.Timestamp(TRAIN_START)
T1 = pd.Timestamp(VAL_END)  # kilitli sabit (2023-06-30 00:00 UTC); varsayim YOK
COST = 0.003  # kilitli (spot round-trip)


def causality_probe_p10():
    import inspect
    import phase10_preflight as _s  # noqa
    src = inspect.getsource(main) + inspect.getsource(gen_schedule)
    for bad in (".shift(-", "ewm(center=", "future_return", "close["):
        assert bad not in src, f"yasak operator: {bad}"


def gen_schedule(grid):
    """grid: set(int ms). Donus: {kural: [(entry_ms, exit_ms)]}. Fiyat YOK."""
    g = sorted(grid)
    gmin, gmax = g[0], g[-1]
    ev = {"E1": [], "E2": [], "E3": []}
    d = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 6, 30, 23, 55, tzinfo=timezone.utc)
    while d <= end:
        ms = int(d.timestamp() * 1000)
        wd, hm = d.weekday(), (d.hour, d.minute)
        if wd == 4 and hm == (23, 55):  # Cuma
            sun = d + timedelta(days=2)
            ex = int(sun.timestamp() * 1000)
            if ms in grid and ex in grid:
                ev["E1"].append((ms, ex))
        if hm == (0, 0):  # gunluk E2
            ex = ms + 8 * 3600 * 1000
            if ms in grid and ex in grid:
                ev["E2"].append((ms, ex))
        if d.hour % 8 == 0 and hm[1] == 0 and d.minute == 0:  # settlement E3
            ex = ms + 3 * 3600 * 1000
            if ms in grid and ex in grid:
                ev["E3"].append((ms, ex))
        d += timedelta(minutes=5)
    return ev


def max_concurrent(intervals):
    pts = []
    for a, b in intervals:
        pts.append((a, 1))
        pts.append((b, -1))
    pts.sort()
    cur = mx = 0
    for _, dl in pts:
        cur += dl
        mx = max(mx, cur)
    return mx


def main():
    D10.mkdir(parents=True, exist_ok=True)
    causality_probe_p10()
    print("causality probe PASS (takvim-only uretim)", flush=True)
    spot = load_dataset_slice()[["date"]]  # FIYAT YOK, sadece zaman
    ts = pd.to_datetime(spot["date"])
    ts = ts.dt.tz_localize("UTC") if getattr(ts.dt, "tz", None) is None else ts
    grid = set(to_ms(ts))
    assert min(grid) == int(T0.timestamp() * 1000) and max(grid) == int(T1.timestamp() * 1000)
    print(f"grid: {len(grid)} bar {T0} -> {T1}", flush=True)
    ev = gen_schedule(grid)
    out = {"rules": {}, "cost_per_hold": COST, "fdr_family": ["E1", "E2", "E3"]}
    for k, iv in ev.items():
        n = len(iv)
        mc = max_concurrent(iv)
        out["rules"][k] = {"n_events": n, "max_concurrent": mc,
                           "first": str(pd.to_datetime(iv[0][0], unit="ms", utc=True)),
                           "last_entry": str(pd.to_datetime(iv[-1][0], unit="ms", utc=True))}
        print(f"  {k}: n={n} maxconcurrent={mc}", flush=True)
        assert mc == 1, f"STOP: {k} kural-ici overlap"
    # capraz-overlap orani (betimsel): herhangi 2 kuralin ayni anda acik oldugu barlar
    allbars = set()
    for iv in ev.values():
        for a, b in iv:
            allbars.add((a, b))
    # E1+E2 kesisimi: E1 araligina dusen E2 girisleri
    e1span = [(a, b) for a, b in ev["E1"]]
    cross = sum(1 for a, _ in ev["E2"] if any(x <= a < y for x, y in e1span))
    out["cross_overlap"] = {"E2_entries_inside_E1_holds": cross,
                            "policy": "bagimsiz portfoyler, netting YOK"}
    print(f"  capraz: E1-ici E2 girisi={cross} (bagimsiz kol, netting yok)", flush=True)
    # settlement capraz-kontrol (6B manifest; yeni indirme YOK)
    man = json.load(open(ROOT / "experiments/phase_06_market_context/6B_funding/data/MANIFEST_DOWNLOAD_6B.json",
                         encoding="utf-8"))
    out["settlement_xcheck"] = {"archive_settlements": man["n_settlements"],
                                "E3_events": len(ev["E3"]),
                                "note": "E3 takvimi sabit 00/08/16 gridinden; arsiv 8h-grid dogrulamali"}
    print(f"  settlement: arsiv={man['n_settlements']} E3event={len(ev['E3'])}", flush=True)
    # guc on-hesabi (d=0.30, tek-yonlu alfa 0.05; mevcut power makinesi esdegeri)
    from statsmodels.stats.power import TTestPower
    pw = TTestPower()
    for k in ("E1", "E2", "E3"):
        n = out["rules"][k]["n_events"]
        pwr = float(pw.power(effect_size=0.30, nobs=n, alpha=0.05, alternative="larger"))
        out["rules"][k]["power_d030"] = round(pwr, 4)
        print(f"  {k}: power(d=0.30)={pwr:.4f} {'OK' if pwr >= 0.80 else 'YETERSIZ'}", flush=True)
    with open(D10 / "PREFLIGHT10.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    # event takvimi artefakti (tarih-only; getiri YOK)
    rows = []
    for k, iv in ev.items():
        for a, b in iv:
            rows.append({"rule": k, "entry": str(pd.to_datetime(a, unit="ms", utc=True)),
                         "exit": str(pd.to_datetime(b, unit="ms", utc=True))})
    pd.DataFrame(rows).to_parquet(D10 / "events10.parquet", index=False)
    print(f"YAZILDI: PREFLIGHT10.json + events10.parquet ({len(rows)} event)", flush=True)


if __name__ == "__main__":
    main()
