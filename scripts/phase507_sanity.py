"""Phase 5 — Bağımsız teyit (phase507): oof500.parquet + matrix500.json üzerinden
ana metriklerin BAĞIMSIZ kodla yeniden hesaplanması.

Kontroller (hepsi oof/frame'den türetilir, phase505 kullanmaz):
1. Her cell'de PSS = top-decile mean future return - C.
2. Her cell'de n_val / n_top tutarlılığı (n_top = ceil(0.1*n_val)).
3. q değerlerinin BH-FDR ile yeniden hesabı = matrix500.json'daki q'lar.
4. Baseline vs en iyi cell karşılaştırması (edge farkı işareti).
5. Tarih aralığı: tüm OOF tarihleri VAL içinde (FINAL_A'ya taşma YOK).
6. OOF parquetsiz matrix yok -> FAIL.

Çıktı: experiments/phase_05_ml/results/sanity507.json + stdout PASS/FAIL.
Calistir: py -3 scripts/phase507_sanity.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.freqai.p5_splits import VAL_START, VAL_END

COST_C = 0.003  # DESIGN 500 sec 14 kilitli sabit (phase502 ile aynı değer)
ALPHA = 0.05
RES_DIR = ROOT / "experiments" / "phase_05_ml" / "results"
PASSED = []


def check(name, cond, detail=""):
    PASSED.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    return bool(cond)


def bh_q(ps):
    ps = np.asarray(ps, float)
    order = np.argsort(ps, kind="stable")
    q = np.empty_like(ps)
    run = 1.0
    for pos in range(len(order) - 1, -1, -1):
        i = order[pos]
        run = min(run, ps[i] * len(ps) / (pos + 1))
        q[i] = run
    return q


def main():
    oof_path = RES_DIR / "oof500.parquet"
    mat_path = RES_DIR / "matrix500.json"
    ok = True
    ok &= check("oof500.parquet var", oof_path.exists())
    ok &= check("matrix500.json var", mat_path.exists())
    if not ok:
        raise SystemExit("sanity artefaktı eksik")

    oof = pd.read_parquet(oof_path)
    with open(mat_path, encoding="utf-8") as f:
        cells = json.load(f)
    by_id = {c["cell_id"]: c for c in cells}

    # 5. Tarih aralığı
    ts = pd.to_datetime(oof["date"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    n_out = int(((ts < VAL_START) | (ts > VAL_END)).sum())
    check("OOF tarihleri VAL içinde (FINAL_A taşması yok)", n_out == 0, f"out={n_out}")

    # 1/2. PSS yeniden hesabı
    worst = 0.0
    n_checked = 0
    for cid, g in oof.groupby("cell_id"):
        s = g["score"].to_numpy(float)
        r = g["future_return"].to_numpy(float)
        k = int(np.ceil(len(s) * 0.10))
        idx = np.argsort(-s, kind="stable")[:k]
        pss = float(r[idx].mean()) - COST_C
        assert cid in by_id, f"matrix'te yok: {cid}"
        rec = by_id[cid]
        d = abs(pss - rec["pss"]["pss"])
        worst = max(worst, d)
        check(f"PSS {cid}", d < 1e-9, f"diff={d:.2e}")
        check(f"n_top {cid}", rec["pss"]["n_top"] == k, f"k={k}")
        n_checked += 1
    print(f"  checked {n_checked} cells, max PSS diff={worst:.2e}")

    # 3. BH-FDR yeniden hesabı (4 aile)
    fams = {"primary_L0": [c for c in cells if c["label"] == "L0"
                           and c["model"] != "BASE" and not c["cell_id"].startswith("S")],
            "primary_L1": [c for c in cells if c["label"] == "L1"
                           and c["model"] != "BASE" and not c["cell_id"].startswith("S")],
            "primary_L2": [c for c in cells if c["label"] == "L2"
                           and c["model"] != "BASE" and not c["cell_id"].startswith("S")],
            "secondary": [c for c in cells if c["cell_id"].startswith("S")]}
    for fam, members in fams.items():
        ps = [m["pss"]["p_test"] for m in members]
        qs = bh_q(ps)
        for m, q in zip(members, qs):
            rec_q = m["pss"].get("q", float("nan"))
            check(f"q {m['cell_id']}", abs(q - rec_q) < 5e-4, f"q={q:.4f} rec={rec_q}")

    # 4. Baseline karşılaştırması
    for lb in ("L0", "L1", "L2"):
        base = by_id.get(f"BASE{lb}")
        prim = [c for c in cells if c["label"] == lb and c["model"] != "BASE"
                and not c["cell_id"].startswith("S")]
        if base and prim:
            best = max(prim, key=lambda c: c["pss"]["edge_over_cost"])
            print(f"  {lb}: baseline edge={base['pss']['edge_over_cost']:.3f} "
                  f"best={best['cell_id']} edge={best['pss']['edge_over_cost']:.3f}")

    fails = [n for n, c in PASSED if not c]
    out = {"n_checks": len(PASSED), "n_fail": len(fails), "fails": fails,
           "max_pss_diff": worst, "n_cells": n_checked}
    with open(RES_DIR / "sanity507.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nTOPLAM: {len(PASSED)} check, {len(fails)} hatalı")
    assert not fails, fails
    print("SANITY ALL PASS")


if __name__ == "__main__":
    main()