"""M.20 INDEPENDENT CONFIRMATION — 2025H1 execution (protocol-locked).

Yetkili acilis: M.20 emri (2025H1 confirmation penceresi). Baska pencere YOK.
Adimlar:
 0. holdout hash + exact-bounds teyidi (STOP if fail)
 1. funding arsivi 2025-01-01 -> 2025-07-01T00:00 uzatma (sinir settlement
    icin; ayni endpoint, pencere-assert'li; fiyat verisi DEGIL)
 2. H48 TRAIN fit (2020-2022, M2/s42, frozen) + q90==0.592775 teyidi (1e-12,
    STOP if fail) = bit-exact reproduction gate
 3. 2025H1: B3 feature (frozen) + L1@H48 label + bound kesimi + dropna
    (warmup kaybi raporlu; protected 2024 verisi YOK)
 4. Skorlar (frozen model) + frozen q90 esigi -> eventler
 5. Metrikler: PSS/edge(decile+event), AUC/IC/tau/d/power/q(tek test),
    theta + block CI (K=500, 10k, s42), MaxDD, turnover, gross/cost,
    breakeven/marj
 6. Gate zinciri (WF: YAPISAL N/A — 181-gun pencere 365-gun train barindiramaz,
    protected 2024 kullanilamaz; seed gate aynen) -> CONFIRMED/NOT-CONFIRMED/STOP

YASAK: phase_m20_replication.py kullanimi (bakilmaz, calistirilmaz),
  yeni fit-disi model, tuning, baska pencere, holdout-disi fiyat verisi.

Calistir: py -3 scripts/phase_m20_confirm.py (arka planda + log)
"""
import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase501_features import BLOCKS, build_features as build_b3
from phase502_labels import (compute_labels, label_bound_mask, COST_C,
                             H_PRIMARY as _H12, TF_MINUTES)
from phase503_models import make_model, fit_predict, M2
from phase505_stats import (cell_metrics, pss_stats, benjamini_hochberg,
                            ALPHA)
from phase6a_run import split_arm
from phase7_run import block_bootstrap_theta, event_metrics
from src.freqai.p5_splits import (verify_holdout_hash, HOLDOUT_FEATHER,
                                  FINAL_P5_START, FINAL_P5_END,
                                  TRAIN_START, TRAIN_END)
from src.timeconv import to_ms

A20 = ROOT / "experiments" / "phase_m20_execution"
RESC = A20 / "results_confirm"
DATAC = A20 / "data_confirm"
H = 48
SEED = 42
Q90_FROZEN = 0.5927749364886543  # RESULTS_7.json extra (tam presizyon; kisaltilmis 0.592775 DEGIL)
N_BOOT, BK = 10000, 500
CPU_CAP = 12.0
LEDGER = []
VAL_DAYS = 181  # 2025H1 = 181 gun (artik-yil degil)
FEE_RT, SPREAD_RT, SLIP_RT = 0.0008, 0.0001, 0.0004
C_FIX = FEE_RT + SPREAD_RT + SLIP_RT
FAPI = "https://fapi.binance.com/fapi/v1/fundingRate"


def download_funding(sym="BTCUSDT"):
    DATAC.mkdir(parents=True, exist_ok=True)
    start = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp() * 1000)
    end = int(pd.Timestamp("2025-07-01 00:00:00", tz="UTC").timestamp() * 1000)
    assert end == 1751328000000, "sinir settlement penceresi"
    rows, cursor, pages = [], start, 0
    while True:
        url = (f"{FAPI}?symbol={sym}&startTime={cursor}&endTime={end}&limit=1000")
        assert cursor >= start, "pencere disi istek"
        req = urllib.request.Request(url, headers={"User-Agent": "zen-genie-m20c/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            page = json.loads(r.read().decode())
        assert isinstance(page, list) and page, "STOP: funding sayfasi bos"
        pages += 1
        for rec in page:
            rows.append((int(rec["fundingTime"]), float(rec["fundingRate"])))
        cursor = max(int(x["fundingTime"]) for x in page) + 1
        if len(page) < 1000 or cursor > end:
            break
        time.sleep(0.3)
    df = pd.DataFrame(rows, columns=["funding_ms", "funding_rate"])
    df = df.drop_duplicates("funding_ms").sort_values("funding_ms").reset_index(drop=True)
    assert int(df["funding_ms"].iloc[0]) <= start + 8 * 3600 * 1000, "STOP: kapsama basi"
    assert int(df["funding_ms"].iloc[-1]) >= end - 8 * 3600 * 1000, "STOP: sinir settlement yok"
    gaps = df["funding_ms"].diff().dropna().to_numpy() / 1000.0
    assert ((gaps >= 8 * 3600 - 60) & (gaps <= 8 * 3600 + 60)).all(), "STOP: eksik settlement"
    df.to_parquet(DATAC / "funding_2025H1.parquet", index=False)
    print(f"  funding: {len(df)} settlement, {pages} page", flush=True)
    return df


def main():
    t_start = time.time()
    RESC.mkdir(parents=True, exist_ok=True)
    print("== M.20 CONFIRM (2025H1, frozen H48 pipeline) ==", flush=True)

    # 0. holdout butunlugu
    verify_holdout_hash()
    print("  holdout hash OK", flush=True)
    px = pd.read_feather(HOLDOUT_FEATHER)
    ts = pd.to_datetime(px["date"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    px["date"] = ts
    assert ts.min() == FINAL_P5_START and ts.max() == FINAL_P5_END, "STOP: pencere"
    assert ((ts >= FINAL_P5_START) & (ts <= FINAL_P5_END)).all(), "STOP: sizinti"
    print(f"  holdout: {len(px)} bar {ts.min()} -> {ts.max()}", flush=True)

    # 1. funding uzatma
    fund = download_funding()
    fms = fund["funding_ms"].to_numpy(dtype="int64")
    frt = fund["funding_rate"].to_numpy(float)

    # 2. frozen TRAIN fit + q90 teyidi
    from phase502_labels import build_frame
    f5 = build_frame(tf_minutes=5, horizon=H)
    dtr = split_arm(f5, BLOCKS["B3"], label="L1", horizon=H)
    t0 = time.process_time()
    est, _ = make_model(M2, "L1", SEED)
    sc_tr, fitted, _ = fit_predict(est, None, dtr["X_train"], dtr["y_train"], dtr["X_train"])
    LEDGER.append({"arm": "H48-train-refit", "cpu_sec": round(time.process_time() - t0, 1)})
    q90 = float(np.quantile(sc_tr, 0.90))
    print(f"  q90 recomputed={q90:.12f} frozen={Q90_FROZEN}", flush=True)
    if abs(q90 - Q90_FROZEN) >= 1e-12:
        raise RuntimeError(f"STOP: reproducibility failure (q90 diff={abs(q90-Q90_FROZEN):.2e})")

    # 3. confirmation frame (B3 frozen + L1@H48 + bound + dropna)
    feats = build_b3(px).reset_index(drop=True)
    labs = compute_labels(px, H).reset_index(drop=True)
    frame = feats.join(labs)
    frame["date"] = pd.to_datetime(px["date"]).to_numpy()
    tsf = pd.to_datetime(frame["date"])
    if getattr(tsf.dt, "tz", None) is None:
        tsf = tsf.dt.tz_localize("UTC")
    cutoff = FINAL_P5_END - pd.Timedelta(minutes=H * TF_MINUTES)
    cmask = (tsf >= FINAL_P5_START) & (tsf <= cutoff)
    cf = frame.loc[cmask].copy().reset_index(drop=True)
    n_pre = len(cf)
    cf = cf.dropna(subset=BLOCKS["B3"] + ["L1"]).reset_index(drop=True)
    print(f"  conf: pencere-ici {n_pre} -> dropna sonrasi {len(cf)} "
          f"(warmup kaybi {n_pre - len(cf)})", flush=True)
    assert ((pd.to_datetime(cf["date"]) >= FINAL_P5_START)
            & (pd.to_datetime(cf["date"]) <= FINAL_P5_END)).all(), "STOP: sizinti"

    # 4. skorlar + eventler (frozen model + frozen esik)
    t0 = time.process_time()
    Xc = cf[BLOCKS["B3"]].to_numpy()
    Xtr = dtr["X_train"]
    scores = fitted.predict(Xc)
    LEDGER.append({"arm": "H48-confirm-infer", "cpu_sec": round(time.process_time() - t0, 1)})
    ev_mask = scores >= Q90_FROZEN
    fut = cf["future_return"].to_numpy()
    n_conf = len(cf)

    # 5a. funding-per-event + cost
    cms = to_ms(cf["date"])
    t_end = cms + H * 5 * 60 * 1000
    ii = np.searchsorted(fms, cms, side="right")
    ee = ev_mask
    fcost_all = np.zeros(n_conf)
    has_all = np.zeros(n_conf, bool)
    jj = np.searchsorted(fms, t_end, side="right")
    has_all = jj > ii
    fcost_all[has_all] = np.array([frt[ii[k]] if jj[k] - ii[k] == 1 else
                                   frt[ii[k]:jj[k]].sum() for k in np.where(has_all)[0]])
    r_ev = fut[ev_mask] - (C_FIX + fcost_all[ev_mask])
    c_avg = float(C_FIX + fcost_all[ev_mask].mean()) if ev_mask.sum() else C_FIX
    n = int(ev_mask.sum())
    lam = n * 365.0 / VAL_DAYS
    print(f"  events={n} (rate={n/n_conf:.4f}) C_conf_avg={c_avg:.7f} "
          f"funding_ort={fcost_all[ev_mask].mean():+.7f}", flush=True)

    # 5b. metrikler
    met = cell_metrics(scores, cf["L1"].to_numpy(), fut, "L1", "B3", M2,
                       cost=c_avg, seed=SEED, cell_id="CONF-H48")
    met["n_train"] = dtr["n_train"]
    p = met["pss"]
    auc, ic, tau = met["auc"], met["rank_ic"], met["kendall_tau"]
    mu, sd = r_ev.mean(), r_ev.std(ddof=1)
    theta = float(mu / sd * np.sqrt(lam)) if sd > 0 and n > 1 else 0.0
    # block bootstrap (K=500 event, 10k, s42) — n<K ise validity STOP
    rng = np.random.default_rng(SEED)
    K = BK
    if n < K:
        raise RuntimeError(f"STOP: yetersiz event (n={n} < K={K})")
    nblocks = int(np.ceil(n / K))
    outs = np.empty(N_BOOT)
    for b in range(N_BOOT):
        st_ = rng.integers(0, n - K + 1, nblocks)
        idx = np.concatenate([np.arange(x, x + K) for x in st_])[:n]
        sm = r_ev[idx]
        outs[b] = sm.mean() / sm.std(ddof=1) * np.sqrt(lam) if sm.std(ddof=1) > 0 else np.nan
    lo, hi = np.nanpercentile(outs, [2.5, 97.5])
    eq = np.cumsum(r_ev)
    maxdd = float(-(eq - np.maximum.accumulate(eq)).min())
    gross = float(fut[ev_mask].mean())
    net = float(mu)
    mean10 = float(fut[np.argsort(-scores, kind="stable")[:max(1, int(np.ceil(n_conf*0.10)))]].mean())
    edge_dec = (mean10 - c_avg) / c_avg
    edge_ev = net / c_avg
    top1_share = float(np.sort(r_ev)[-max(1, n // 100):].sum() / r_ev.sum()) if r_ev.sum() > 0 else float("nan")
    print(f"  theta={theta:+.4f} CI95=[{lo:+.4f},{hi:+.4f}] net={net:+.6f} "
          f"gross={gross:+.6f} maxdd={maxdd:.4f} top1pay={top1_share:.3f}", flush=True)
    print(f"  decile: mean10={mean10:+.6f} edge={edge_dec:.3f} auc={auc:.4f} ic={ic:.4f}", flush=True)

    # 6. gate zinciri (WF: YAPISAL N/A — asagida kayitli)
    from phase505_stats import benjamini_hochberg as _bh
    q = float(_bh([p["p_test"]])[0])
    gates = {
        "a_pss_edge": bool(p["pss"] > 0 and edge_dec >= 1.2 and net > 0 and edge_ev >= 1.2),
        "b_support": bool(auc >= 0.55 and ic >= 0.01 and tau > 0),
        "c_theta": bool(lo > 0),
        "d_effect": bool(p["cohens_d"] >= 0.30 and p["power"] >= 0.80),
        "e_fdr": bool(q < ALPHA),
        "f_maxdd": bool(maxdd <= 0.20),
        "wf": "N/A (181-gun pencere 365-gun train barindiramaz; protected 2024 kullanilamaz)",
    }
    chain = all(v for k, v in gates.items() if k != "wf")
    print(f"  GATES {gates} chain(computable)={chain}", flush=True)

    decision = "FAIL"
    extra = {}
    if chain:
        seed_pss = {}
        for sd in (42, 7, 123):
            est2, _ = make_model(M2, "L1", sd)
            t0s = time.process_time()
            scc, _, _ = fit_predict(est2, None, dtr["X_train"], dtr["y_train"], Xc)
            LEDGER.append({"arm": f"H48-confirm-seed{sd}",
                           "cpu_sec": round(time.process_time() - t0s, 1)})
            sm = cell_metrics(scc, cf["L1"].to_numpy(), fut, "L1", "B3", M2,
                              cost=c_avg, seed=sd, cell_id=f"CONF-s{sd}")
            seed_pss[str(sd)] = sm["pss"]["pss"]
        signs = [1 if v > 0 else 0 for v in seed_pss.values()]
        extra["seed_consistency"] = {"frac": sum(signs) / len(signs),
                                     "pass": sum(signs) / len(signs) >= 2 / 3}
        decision = "PASS" if extra["seed_consistency"]["pass"] else "FAIL"
        print(f"  seeds={extra['seed_consistency']} -> {decision}", flush=True)

    verdict = {"PASS": "CONFIRMED", "FAIL": "NOT-CONFIRMED",
               "STOP": "STOP"}[decision]
    total_cpu = sum(x["cpu_sec"] for x in LEDGER)
    budget = {"cpu_hours": round(total_cpu / 3600, 4), "ledger": LEDGER}
    out = {"decision": decision, "verdict": verdict,
           "theta": round(theta, 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
           "net": round(net, 7), "gross": round(gross, 7),
           "edge_event": round(float(edge_ev), 4), "edge_decile": round(float(edge_dec), 4),
           "c_conf_avg": round(c_avg, 7),
           "auc": round(float(auc), 4), "rank_ic": round(float(ic), 4),
           "tau": round(float(tau), 4), "d": round(float(p["cohens_d"]), 4),
           "power": round(float(p["power"]), 3), "q": round(q, 4),
           "maxdd": round(maxdd, 4), "n_events": n, "n_conf": n_conf,
           "event_rate": round(float(n / n_conf), 4),
           "top1_share": round(float(top1_share), 4),
           "breakeven_event": round(gross, 7),
           "gates": gates, "extra": extra, "budget": budget,
           "q90_frozen": Q90_FROZEN, "lock": "M20-CONFIRM", "window": "2025H1"}
    with open(RESC / "RESULTS_CONFIRM.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    with open(RESC / "GATE_CONFIRM.json", "w", encoding="utf-8") as f:
        json.dump({"gates": gates, "decision": decision, "verdict": verdict}, f, indent=2, default=str)
    pd.DataFrame({"date": pd.to_datetime(cf["date"]), "score": scores,
                  "label_y": cf["L1"].to_numpy(), "future_return": fut,
                  "event": ev_mask}).to_parquet(RESC / "oof_confirm.parquet")
    manifest = {"window": "2025H1", "seed": SEED, "decision": decision,
                "verdict": verdict, "cpu_hours": budget["cpu_hours"],
                "wf": "N/A (yapisal)", "replication_py": "KULLANILMADI (existence-notu)"}
    with open(RESC / "MANIFEST_CONFIRM.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    write_report(out)
    print(f"\nKarar: {verdict}\nCPU: {budget['cpu_hours']:.3f} cpu-sa "
          f"duvar: {(time.time()-t_start)/60:.1f} dk", flush=True)


def write_report(out):
    md = []
    md.append("# M.20 INDEPENDENT CONFIRMATION — RESULTS (2025H1)")
    md.append("")
    md.append(f"**Karar:** {out['verdict']}")
    md.append(f"**theta:** {out['theta']:+.4f} CI95={out['ci95']} "
              f"(K=500 event-blok, 10k, s42)")
    md.append(f"**net (event):** {out['net']:+.6f} (gross {out['breakeven_event']:+.6f} "
              f"- C {out['c_conf_avg']:.7f}) | edge_event {out['edge_event']:.3f} / "
              f"edge_decile {out['edge_decile']:.3f}")
    md.append(f"**MaxDD:** {out['maxdd']} (gate ≤0.20) | **events:** {out['n_events']} "
              f"(rate {out['event_rate']}) | top1-pay {out['top1_share']}")
    md.append(f"**AUC:** {out['auc']} **IC:** {out['rank_ic']} **tau:** {out['tau']} "
              f"**d:** {out['d']} **power:** {out['power']} **q:** {out['q']}")
    md.append(f"**Gates:** {out['gates']}")
    md.append(f"**Karar:** {out['decision']} → {out['verdict']}")
    md.append("")
    md.append("Notlar: WF yapisal N/A (gerekce GATE_CONFIRM icinde); "
              "phase_m20_replication.py KULLANILMADI (untouched, existence-notu); "
              "Phase 7 ve M.20 sonuclari degistirilmedi; P5 bu amacla tuketildi — "
              "yeni final test ayri M.20 ister.")
    with open(A20 / "M20_INDEPENDENT_CONFIRMATION_RESULTS.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    main()