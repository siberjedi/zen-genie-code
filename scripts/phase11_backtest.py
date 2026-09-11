"""Phase 11 BACKTEST — frozen carry (12 CM quarterly). ILK P&L HESABI.

Kollar yok (tek always-on tasarim); birim = ceyrek (n=12).
Giris: ceyrek-basi ilk bar (close). Cikis: settlement-oncesi son bar
(open < vade-Cuma 08:00 UTC). Settlement-sonrasi barlar KESILIR.
Fiyatlar: perp = quarterly close; spot = +55dk 5m close (eszamanli, kanitli).
NUMERAIRE: BTC (kilitli). Servet = Q/s0 + W0 (maliyet-ONCESI).
Q_USD = 100000 (olcek-serbest metrikleri etkilemez).
Marjin: izole, W0 = k*Q/p0f BTC (k=10 kilitli), MMR %0.5, breach -> likidasyon
(o barda kapat, kurtarma YOK). Fee: spot %0.10, perp %0.05 (donem tarifesi);
slip 2bp/fill/bacak (fiyatlara gomulu + AYRI kalem raporlu).
Havuzlanan birim: ceyrek GETIRISI (net_btc/committed_btc) — donemler arasi
10x olcek farki mutlak BTC ile havuzlanamaz.
Ag I/O YOK (craw + feather yerelde olmali; eksikse STOP).

Calistir: py -3 scripts/phase11_backtest.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase502_labels import load_dataset_slice
from src.timeconv import to_ms

D11 = ROOT / "experiments" / "phase_11_basis" / "data"
R11 = ROOT / "experiments" / "phase_11_basis" / "results11"
Q_USD = 100000.0
K_MARGIN, MMR = 10.0, 0.005
FEE_SPOT, FEE_PERP, SLIP = 0.0010, 0.0005, 0.0002
QUARTERS = [
    ("BTCUSD_200925", "2020-07-01", "2020-09-25"), ("BTCUSD_201225", "2020-10-01", "2020-12-25"),
    ("BTCUSD_210326", "2021-01-01", "2021-03-26"), ("BTCUSD_210625", "2021-04-01", "2021-06-25"),
    ("BTCUSD_210924", "2021-07-01", "2021-09-24"), ("BTCUSD_211231", "2021-10-01", "2021-12-31"),
    ("BTCUSD_220325", "2022-01-01", "2022-03-25"), ("BTCUSD_220624", "2022-04-01", "2022-06-24"),
    ("BTCUSD_220930", "2022-07-01", "2022-09-30"), ("BTCUSD_221230", "2022-10-01", "2022-12-30"),
    ("BTCUSD_230331", "2023-01-01", "2023-03-31"), ("BTCUSD_230630", "2023-04-01", "2023-06-30"),
]
ALPHA = 0.05


def run_quarter(px_ms, px_fut, px_spot, settle_ms):
    """Deterministik ceyrek muhasebesi — BTC numeraire, exact cost audit."""
    fms = np.asarray(px_ms)
    fp = np.asarray(px_fut, float)
    sp = np.asarray(px_spot, float)
    n = len(fms)
    assert n > 100
    p0, s0 = fp[0], sp[0]
    xi = int(np.where(fms < settle_ms)[0][-1])
    assert xi > 100, "pencere cok kisa"
    pT, sT = fp[xi], sp[xi]
    nc = Q_USD / 100.0
    s_in, s_out = s0 * (1 + SLIP), sT * (1 - SLIP)
    p_in, p_out = p0 * (1 - SLIP), pT * (1 + SLIP)
    btc_qty = Q_USD * (1 - FEE_SPOT) / s_in
    c_spot_in = Q_USD / s0 - btc_qty
    fee_in = FEE_PERP * Q_USD / p_in
    W0 = K_MARGIN * Q_USD / p_in
    start_btc = Q_USD / s0 + W0
    pu = fp[:xi + 1]
    uw = W0 - fee_in + nc * 100.0 * (1.0 / pu - 1.0 / p_in)
    ratio = uw * pu / Q_USD
    liq = np.where(ratio <= MMR)[0]
    out = {"entry_basis": (p0 - s0) / s0, "exit_basis": (pT - sT) / sT,
           "s0": float(s0), "p0f": float(p0), "sT": float(sT),
           "n_bars": int(xi + 1),
           "committed_btc": float(Q_USD / s0 + W0)}
    if len(liq):
        b = int(liq[0])
        pl = fp[b]
        fee_out = FEE_PERP * Q_USD / pl
        wallet = W0 - fee_in + nc * 100.0 * (1.0 / pl - 1.0 / p_in) - fee_out
        c_spot_out = btc_qty - btc_qty * (1 - SLIP) * (1 - FEE_SPOT)
        c_perp_slip = (nc * 100.0 * (1.0 / pl - 1.0 / p0)
                       - nc * 100.0 * (1.0 / (pl * (1 + SLIP)) - 1.0 / p_in))
        end_btc = btc_qty * (1 - SLIP) * (1 - FEE_SPOT) + wallet
        out.update({"liquidated": True, "liq_bar": b, "liq_ms": int(fms[b]),
                    "wallet_end_btc": float(wallet),
                    "net_btc": float(end_btc - start_btc),
                    "cost_btc": float(c_spot_in + c_spot_out + fee_in + fee_out
                                      + c_perp_slip)})
        return out
    fee_out = FEE_PERP * Q_USD / p_out
    wallet = W0 - fee_in + nc * 100.0 * (1.0 / p_out - 1.0 / p_in) - fee_out
    c_spot_out = btc_qty - btc_qty * (1 - SLIP) * (1 - FEE_SPOT)
    c_perp_slip = (nc * 100.0 * (1.0 / pT - 1.0 / p0)
                   - nc * 100.0 * (1.0 / p_out - 1.0 / p_in))
    end_btc = btc_qty * (1 - SLIP) * (1 - FEE_SPOT) + wallet
    out.update({"liquidated": False,
                "wallet_end_btc": float(wallet),
                "net_btc": float(end_btc - start_btc),
                "cost_btc": float(c_spot_in + c_spot_out + fee_in + fee_out
                                  + c_perp_slip)})
    return out


def self_check():
    """Duz-fiyat sentetik ceyrek: net + cost == 0 (tol 1e-9 BTC)."""
    n = 2000
    ms = np.arange(n, dtype="int64") * 3600000
    fut = np.full(n, 30000.0)
    spt = np.full(n, 30000.0)
    r = run_quarter(ms, fut, spt, ms[-1] + 3600000)
    assert not r["liquidated"], "sentetik likidasyon imkansiz"
    diff = abs(r["net_btc"] + r["cost_btc"])
    assert diff < 1e-9, f"muhasebe kimligi bozuk: {diff}"
    print(f"self-check PASS (BTC kimligi diff={diff:.2e})", flush=True)


def main():
    R11.mkdir(parents=True, exist_ok=True)
    self_check()
    spot = load_dataset_slice()[["date", "close"]]
    sms = to_ms(spot["date"])
    S = spot["close"].to_numpy(float)
    recs = []
    for sym, qstart, exp in QUARTERS:
        df = pd.read_parquet(D11 / "craw" / f"{sym}.parquet")
        fms = df["open_ms"].to_numpy()
        settle = int(pd.Timestamp(exp + " 08:00", tz="UTC").value // 10**6)
        m = (fms >= int(pd.Timestamp(qstart, tz="UTC").value // 10**6)) & (fms < settle)
        assert m.sum() > 100, f"STOP: {sym} pencere bos"
        tgt = fms[m] + 55 * 60 * 1000
        pos = np.searchsorted(sms, tgt)
        inb = pos < len(sms)
        okm = np.zeros(int(m.sum()), bool)
        okm[inb] = sms[pos[inb]] == tgt[inb]
        assert okm.mean() > 0.99, f"STOP: {sym} hizalama"
        subm = np.where(m)[0][okm]
        r = run_quarter(fms[subm], df["close"].to_numpy()[subm], S[pos[okm]], settle)
        r["symbol"] = sym
        r["settle"] = exp
        recs.append(r)
        print(f"  {sym}: liq={r['liquidated']} net={r['net_btc']:+.4f}BTC "
              f"entry_basis={r['entry_basis']*1e4:+.1f}bp exit_basis={r['exit_basis']*1e4:+.1f}bp",
              flush=True)
    nets = np.array([r["net_btc"] for r in recs])
    committed = np.array([r["committed_btc"] for r in recs])
    rets = nets / committed
    mean, sd = rets.mean(), rets.std(ddof=1)
    tot_cost = sum(r["cost_btc"] / r["committed_btc"] for r in recs) / len(recs)
    edge = float(mean / tot_cost) if tot_cost > 0 else float("nan")
    from scipy import stats as st
    from statsmodels.stats.power import TTestPower
    tstat, pval = (st.ttest_1samp(rets, 0.0, alternative="greater")
                   if sd > 0 else (0.0, 1.0))
    q = float(pval)  # tek test: BH trivial
    d = float(mean / sd) if sd > 0 else 0.0
    pw = TTestPower()
    power08 = float(pw.power(effect_size=0.80, nobs=len(rets), alpha=ALPHA, alternative="larger"))
    shr = float(mean / sd * np.sqrt(4)) if sd > 0 else 0.0
    rng = np.random.default_rng(42)
    outs = []
    for b in range(10000):
        idx = rng.integers(0, len(rets), len(rets))
        sm = rets[idx]
        outs.append(sm.mean() / sm.std(ddof=1) * 2.0 if sm.std(ddof=1) > 0 else np.nan)
    lo, hi = np.nanpercentile(outs, [2.5, 97.5])
    eq = np.cumsum(rets)
    maxdd = float(-(eq - np.maximum.accumulate(eq)).min())
    liqs = [r["symbol"] for r in recs if r["liquidated"]]
    # program konversiyonlari (tasi-forward, tek-seferlik memo):
    conv_rate = 1 - 1 / ((1 + FEE_SPOT) * (1 + SLIP))
    W0_first = K_MARGIN * Q_USD / (recs[0]["p0f"] * (1 - SLIP))
    conv_in = W0_first * conv_rate
    conv_out = recs[-1].get("wallet_end_btc", 0.0) * conv_rate
    prog_total = float(nets.sum() - conv_in - conv_out)
    gates = {"net_pos": bool(mean > 0), "edge": bool(edge >= 1.2),
             "sharpe_ci": bool(lo > 0), "maxdd": bool(maxdd <= 0.20),
             "d_power": bool(abs(d) >= 0.80 and power08 >= 0.80),
             "fdr": bool(q < ALPHA)}
    gates["chain"] = all(gates.values())
    decision = "PASS" if gates["chain"] else "FAIL"
    out = {"quarters": recs, "n": len(rets),
           "net_mean_btc": round(float(nets.mean()), 6),
           "net_total_btc": round(float(nets.sum()), 6),
           "ret_mean": round(float(mean), 6),
           "program_total_btc": round(prog_total, 6),
           "program_conv_in_btc": round(float(conv_in), 6),
           "program_conv_out_btc": round(float(conv_out), 6),
           "entry_basis_bp_mean": round(float(np.mean([r["entry_basis"] for r in recs]) * 1e4), 1),
           "edge": round(edge, 3), "sharpe_ann": round(shr, 3),
           "sharpe_ci95": [round(float(lo), 3), round(float(hi), 3)],
           "maxdd": round(maxdd, 4), "win_rate": round(float((rets > 0).mean()), 3),
           "turnover_per_year": round(12 / 3.5, 1),
           "d": round(d, 3), "power_d08": round(power08, 3),
           "t": round(float(tstat), 3), "p": float(pval), "q": round(q, 4),
           "liquidated": liqs, "gates": gates, "decision": decision}
    with open(R11 / "RESULTS_11.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    with open(R11 / "GATE_11.json", "w", encoding="utf-8") as f:
        json.dump({"gates": gates, "decision": decision}, f, indent=2, default=str)
    pd.DataFrame([{"symbol": r["symbol"], "net_btc": r["net_btc"],
                   "net_ratio": r["net_btc"] / r["committed_btc"],
                   "liquidated": r["liquidated"],
                   "entry_basis": r["entry_basis"]} for r in recs]).to_parquet(R11 / "oof11.parquet")
    usd_memo = sum(r["net_btc"] * r["sT"] for r in recs)
    md = ["# PHASE 11 — RESULTS (frozen carry, 12 CM quarterly)"]
    md.append("")
    md.append(f"**Karar:** {decision}")
    md.append(f"- net carry (ort/cevrek, oran): {mean:+.6f} | toplam BTC: {nets.sum():+.4f} "
              f"(USD memo ~${usd_memo:,.0f})")
    md.append(f"- program toplami (konversiyonlu): {prog_total:+.4f} BTC")
    md.append(f"- edge: {edge:.3f} | Sharpe_ann: {shr:.3f} CI=[{lo:.3f},{hi:.3f}]")
    md.append(f"- MaxDD: {maxdd:.4f} | win-rate: {(rets > 0).mean():.3f} "
              f"| turnover/yr: {12/3.5:.1f}")
    md.append(f"- likide: {liqs or 'yok'}")
    md.append(f"- p={pval:.4f} q={q:.4f} | d={d:+.3f} power(d=0.8)={power08:.3f}")
    md.append(f"- gate'ler: {gates}")
    for r in recs:
        md.append(f"  - {r['symbol']}: net={r['net_btc']:+.4f}BTC "
                  f"liq={r['liquidated']} giris={r['entry_basis']*1e4:+.0f}bp")
    md.append("")
    md.append("**PHASE 11 CLOSED**" if decision == "FAIL" else "**CANDIDATE-ONLY (tuning/para YOK)**")
    with open(ROOT / "experiments/phase_11_basis/PHASE_11_RESULTS.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Karar: {decision}", flush=True)


if __name__ == "__main__":
    main()
