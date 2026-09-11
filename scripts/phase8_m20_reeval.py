"""M.20 re-evaluation: frozen H48 sinyali, gercekci USD-M futures maliyetiyle.

Girdi (dondurulmus): results7/oof7.parquet (skorlar + eventler, seed42),
  6B funding_btcusdt.parquet (settlement oranlari).
FIT YOK, yeni veri indirme YOK, holdout YOK.

Maliyet (M.20, donem-belgeli):
  fee: taker %0.04 x 2 = 8bp (2020-2023 donem tarifesi; guncel %0.05
    duyarlilik notunda)
  spread: 1bp round-trip (crossing, muhafazakar)
  slippage: 2bp/side = 4bp (kucuk boy merkezi; Phase 8 scout bandi)
  => sabit kisim C_FIX = 13bp = 0.0013
  funding: event basina gerceklesmis (hold 4h funding timestamp keserse
    o settlement orani; LONG yon: oran>0 odeme). Veri 6B arsivinden.
net_i = Y_i - C_FIX - funding_i ; C_M20_avg = C_FIX + mean(funding_i)

Metrikler Phase 7 makinesiyle ayni (event-block bootstrap K=500, 10k, s42).
Karar: A) net<=0 -> H48 STOP | B) net>0 ama edge<1.2 veya CI kapsar ->
  bagimsiz dogrulama | C) net>0 VE edge>=1.2 VE CI-alt>0 -> confirmatory
  tasarimi | D) maliyet guvenilir degil -> STOP.

Calistir: py -3 scripts/phase8_m20_reeval.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase7_run import block_bootstrap_theta  # ayni makine
from src.timeconv import to_ms

A7 = ROOT / "experiments" / "phase_07_horizon"
R7 = A7 / "results7"
DATA6B = ROOT / "experiments" / "phase_06_market_context" / "6B_funding" / "data"

FEE_RT = 0.0008      # taker %0.04 x 2 (donem tarifesi)
SPREAD_RT = 0.0001   # 1bp round-trip crossing
SLIP_RT = 0.0004     # 2bp/side
C_FIX = FEE_RT + SPREAD_RT + SLIP_RT  # 0.0013
N_BOOT, BK, SEED = 10000, 500, 42
VAL_DAYS = 181


def main():
    oof = pd.read_parquet(R7 / "oof7.parquet")
    ev = oof[oof["event"]].reset_index(drop=True)
    n = len(ev)
    fut = ev["future_return"].to_numpy(float)
    gross = float(fut.mean())
    print(f"events={n} gross={gross:+.6f}", flush=True)

    fund = pd.read_parquet(DATA6B / "funding_btcusdt.parquet")
    fms = fund["funding_ms"].to_numpy(dtype="int64")
    frt = fund["funding_rate"].to_numpy(float)
    ems = to_ms(ev["date"])
    ems_ms = ems // 10**6 if ems.max() > 10**15 else ems
    assert ems_ms.min() >= 1577836800000 and ems_ms.max() < 1688169600000, \
        "pencere tasmasi"
    # hold (t, t+4h]: kesilen settlement varsa oranini ode (LONG)
    fcost = np.zeros(n)
    t_end = ems_ms + 4 * 3600 * 1000
    ii = np.searchsorted(fms, ems_ms, side="right")
    jj = np.searchsorted(fms, t_end, side="right")
    has = jj > ii
    fcost[has] = np.array([frt[ii[k]] if jj[k] - ii[k] == 1 else
                           frt[ii[k]:jj[k]].sum() for k in np.where(has)[0]])
    print(f"crossed={int(has.sum())}/{n} funding_ort={fcost.mean():+.7f} "
          f"({fcost.mean()*1e4:+.3f}bp)", flush=True)

    cost_i = C_FIX + fcost
    c_avg = float(cost_i.mean())
    net = fut - cost_i
    lam = n * 365.0 / VAL_DAYS
    mu, sd = net.mean(), net.std(ddof=1)
    theta = float(mu / sd * np.sqrt(lam))
    _, lo, hi = block_bootstrap_theta(net, K=BK, n_boot=N_BOOT, seed=SEED, lam=lam)
    eq = np.cumsum(net)
    maxdd = float(-(eq - np.maximum.accumulate(eq)).min())
    # PSS M.20: top-decile (pooled, tum VAL) - C_M20_avg
    s = oof["score"].to_numpy(float)
    fr_all = oof["future_return"].to_numpy(float)
    kk = int(np.ceil(len(s) * 0.10))
    mean10 = float(fr_all[np.argsort(-s, kind="stable")[:kk]].mean())
    pss_m20 = mean10 - c_avg
    edge = (mean10 - c_avg) / c_avg if c_avg > 0 else float("nan")
    # AUC/rankIC maliyetsiz: Phase 7 kayitli degerler aynen
    r7 = json.load(open(R7 / "RESULTS_7.json", encoding="utf-8"))
    breakeven = gross  # event-bazinda uniform-C net=0 noktasi
    breakeven_decile = mean10  # decile-bazinda uniform-C net=0 noktasi
    margin = breakeven - c_avg
    edge_event = float(mu / c_avg) if c_avg > 0 else float("nan")
    out = {
        "populations": {
            "event_set": "frozen TRAIN-q90, n=647, traded rule (primary)",
            "pooled_decile": "VAL top-decile, n_top=5177, signal-quality continuity",
        },
        "C_M20_avg": round(c_avg, 7), "C_FIX": C_FIX,
        "fee_rt": FEE_RT, "spread_rt": SPREAD_RT, "slip_rt": SLIP_RT,
        "funding_mean": round(float(fcost.mean()), 8),
        "funding_cross_rate": round(float(has.mean()), 4),
        "gross_event": round(gross, 7), "net_event": round(float(mu), 7),
        "gross_decile": round(mean10, 7), "net_decile": round(mean10 - c_avg, 7),
        "theta": round(theta, 4), "ci95": [round(lo, 4), round(hi, 4)],
        "pss_m20": round(pss_m20, 7), "edge_cost_m20_decile": round(edge, 4),
        "edge_cost_m20_event": round(edge_event, 4),
        "auc": r7["cell"]["auc"], "rank_ic": r7["cell"]["rank_ic"],
        "maxdd": round(maxdd, 4), "n_events": n,
        "breakeven_event": round(breakeven, 7),
        "breakeven_decile": round(breakeven_decile, 7),
        "margin_event": round(margin, 7),
        "margin_decile": round(breakeven_decile - c_avg, 7),
        "phase7_net_C0003_event": round(0.005771 - 0.003, 7),
        "phase7_net_C0003_decile": round(0.002341 - 0.003, 7),
    }
    # Karar (tutarli bazda): event-baz birincil; C = tam gate zinciri
    # (edge>=1.2 VE CI-alt>0 VE maxdd<=0.20 VE decile-edge>=1.2) ister.
    full_pass = (edge_event >= 1.2 and lo > 0 and maxdd <= 0.20 and edge >= 1.2)
    if mu <= 0:
        out["decision"] = "A"
        out["verdict"] = "M20 de negatif -> H48 STOP"
    elif full_pass:
        out["decision"] = "C"
        out["verdict"] = "Guclu pozitif -> confirmatory experiment tasarla"
    elif mu > 0:
        out["decision"] = "B"
        out["verdict"] = "Pozitif ama zayif/kirilgan -> bagimsiz dogrulama gerekli"
    else:
        out["decision"] = "D"
        out["verdict"] = "Maliyet guvenilir hesaplanamiyor -> STOP"
    with open(A7 / "M20_REEVAL.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    for k, v in out.items():
        print(f"{k}: {v}", flush=True)


if __name__ == "__main__":
    main()
