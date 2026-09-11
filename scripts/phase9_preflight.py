"""Phase 9 PREFLIGHT — lock spec + executable verification (BACKTEST DEGIL).

Kapsam: muhasebe/risk mekanizmasi kilidi + dogrulama. Sinyal/tuning/threshold
YOK (always-on statik tasarim, scout ledger ile ayni). Holdout YOK.
Karar: mekanizma gecerli + statik tasarim sagkalirsa backtest GO, aksi STOP.

Lock spec (ozet):
 L1 delta hedge: +1 BTC spot / -1 BTC perp (BTC-birim) -> beta=0 yapisal.
 L2 funding: settlement'te aciksa oran uygulanir (LONG: oran>0 oder);
    8h grid aralik-dogrulamali (degisiklik -> STOP).
 L3 basis: giris-cikis farki, funding'den AYRI P&L kalemi.
 L4 execution: 4 fill (spot in/out taker %0.10, perp in/out taker %0.04)
    + slip nominal 2bp/fill/bacak, AYRI kalemler.
 L5 margin: izole, W0 = k x short-notional (senaryo k in {100,200,500}%),
    funding wallet'a swept, MMR %0.5; breach -> likidasyon (pozisyon olur,
    kurtarma YOK). 10x spike testi: giris-notional'ina sentetik 10x sok.
 L6 capital: spot-nakit / futures-wallet / funding-ledger / basis-realized/
    unrealized AYRI defterler.
 L7 rejim: 2020/2021/2022/2023H1 ayri rapor (2022 saklanmaz).
 L8 metrik: net carry, yillik, vol, MaxDD, liq events, funding/basis/cost katkilari.
 L9 STOP: muhasebe-dogrulanamazsa / hedge-bozulursa / margin-modeli
    guvenilmezse / maliyet-sonrasi carry ekonomik degilse STOP.

Calistir: py -3 scripts/phase9_preflight.py (arka planda + log)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

D9 = ROOT / "experiments" / "phase_09_funding_basis" / "data"
FEE_SPOT, FEE_PERP, SLIP, MMR = 0.0010, 0.0004, 0.0002, 0.005
K_SCENARIOS = (1.0, 2.0, 5.0)


def main():
    t0 = time.time()
    out = {"checks": {}, "scenarios": {}, "regimes": {}}
    um = pd.read_parquet(D9 / "um_btcusdt_1h.parquet")
    pj = json.load(open(D9 / "CARRY_SCOUT.json", encoding="utf-8"))
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts"))
    from phase502_labels import load_dataset_slice
    from src.timeconv import to_ms
    spot = load_dataset_slice()[["date", "close"]]
    ts = pd.to_datetime(spot["date"])
    ts = ts.dt.tz_localize("UTC") if getattr(ts.dt, "tz", None) is None else ts
    sms = to_ms(ts)
    pos = np.searchsorted(sms, um["open_ms"].to_numpy() + 55 * 60 * 1000)
    inb = pos < len(sms)
    ok = np.zeros(len(um), bool)
    ok[inb] = sms[pos[inb]] == (um["open_ms"].to_numpy() + 55 * 60 * 1000)[inb]
    # HIZALAMA KURALI: UM[T] <-> spot[T+55dk] (eszamanli close; corr(diff)~0.999
    # kanitli; +0 kaydirma ~0.09 verir). Kural disi birlesme YASAK.
    _S = spot["close"].to_numpy()[pos[ok]]
    _P = um["perp_close"].to_numpy()[ok]
    _c = float(np.corrcoef(np.diff(_S), np.diff(_P))[0, 1])
    assert _c > 0.99, f"STOP: hizalama bozuk (corr={_c:.4f})"
    print(f"hizalama corr(diff)={_c:.4f}", flush=True)
    p = pd.DataFrame({"ms": um["open_ms"].to_numpy()[ok],
                      "perp": um["perp_close"].to_numpy()[ok],
                      "spot": spot["close"].to_numpy()[pos[ok]]}).reset_index(drop=True)
    p["date"] = pd.to_datetime(p["ms"], unit="ms", utc=True)
    S, P = p["spot"].to_numpy(float), p["perp"].to_numpy(float)
    n = len(p)

    # 1. delta hedge dogrulama: dV/dS = 1 - 1 = 0 (yapisal) + sayisal teyit
    port = S - P  # long-spot/short-perp birim deger (BTC-birim hedge)
    beta_num = np.cov(np.diff(S), np.diff(port))[0, 1] / np.var(np.diff(S))
    out["checks"]["delta_beta_vs_spot"] = round(float(beta_num), 6)
    out["checks"]["delta_hedge_ok"] = bool(abs(beta_num) < 0.05)
    print(f"delta beta={beta_num:.4f} (hedef ~0)", flush=True)

    # 2. funding grid + oranlar (6B arsivi aynen)
    f = pd.read_parquet(ROOT / "experiments/phase_06_market_context/6B_funding/data/funding_btcusdt.parquet")
    f = f[(f["funding_ms"] >= p["ms"].iloc[0]) & (f["funding_ms"] <= p["ms"].iloc[-1] + 8 * 3600 * 1000)]
    gaps = np.diff(f["funding_ms"].to_numpy()) / 1000.0
    out["checks"]["funding_interval_8h"] = bool(((gaps >= 8 * 3600 - 60) & (gaps <= 8 * 3600 + 60)).all())
    out["checks"]["n_settlements"] = int(len(f))
    print(f"funding grid 8h: {out['checks']['funding_interval_8h']} ({len(f)} settlement)", flush=True)
    fms = f["funding_ms"].to_numpy(dtype="int64")
    frt = f["funding_rate"].to_numpy(float)

    # 5. margin senaryolari (vektorize): W0=k*p0, funding swept, MMR %0.5
    p0 = P[0]
    # saatlik funding nakdi (short alir +): settlement accomodation
    f_by_bar = np.zeros(n)
    for j in range(len(fms)):
        b = int(np.searchsorted(p["ms"].to_numpy(), fms[j], side="right"))
        if 0 <= b < n:
            ref = P[min(b, n - 1)]
            f_by_bar[b] += frt[j] * ref
    cum_f = np.cumsum(f_by_bar)
    max_exc = float(P.max() / p0)
    out["checks"]["max_excursion_x"] = round(max_exc, 3)
    print(f"maks excursion: {max_exc:.2f}x (giris ${p0:.0f} -> tepe ${P.max():.0f})", flush=True)
    for k in K_SCENARIOS:
        W0 = k * p0
        bal = W0 + cum_f + (p0 - P)  # wallet + unrealized (short: p0-P)
        ratio = bal / P
        liq = np.where(ratio <= MMR)[0]
        if len(liq):
            li = int(liq[0])
            out["scenarios"][f"k{int(k*100)}"] = {
                "survives": False,
                "liq_date": str(p["date"].iloc[li]), "liq_bar": li,
                "liq_price": round(float(P[li]), 1),
                "funding_to_liq_usd": round(float(cum_f[li]), 1),
            }
            print(f"  k={k:.0%}: LIKIDE {p['date'].iloc[li]} @ ${P[li]:.0f}", flush=True)
        else:
            out["scenarios"][f"k{int(k*100)}"] = {
                "survives": True, "min_ratio": round(float(ratio.min()), 4),
                "funding_total_usd": round(float(cum_f[-1]), 1),
            }
            print(f"  k={k:.0%}: sagkaldi (min oran {ratio.min():.3f})", flush=True)
    # 10x spike testi (sentetik, giris aninda): balance=(k-9)*p0 vs MMR*10*p0
    out["spike10x"] = {}
    for k in K_SCENARIOS:
        surv = (k - 9.0) * p0 > MMR * 10 * p0
        out["spike10x"][f"k{int(k*100)}"] = bool(surv)
        print(f"  spike10x k={k:.0%}: {'sagkalir' if surv else 'OLUR'}", flush=True)

    # 3/4/6/7/8. ledger: giris/cikis fee+slip AYRI, basis AYRI, funding AYRI
    s0, sT, pT = S[0], S[-1], P[-1]
    legs = {"spot_in": s0 * FEE_SPOT, "perp_in": p0 * FEE_PERP,
            "spot_out": sT * FEE_SPOT, "perp_out": pT * FEE_PERP,
            "slip": (s0 + p0 + sT + pT) * SLIP}
    basis_pnl = (pT - sT) - (p0 - s0)
    fund_tot = float(cum_f[-1])
    total = fund_tot + basis_pnl - sum(legs.values())
    out["ledger"] = {kk: round(float(vv), 2) for kk, vv in legs.items()}
    out["ledger"]["funding_cash_usd"] = round(fund_tot, 2)
    out["ledger"]["basis_pnl_usd"] = round(basis_pnl, 2)
    out["ledger"]["total_pnl_usd"] = round(total, 2)
    # rejim kirilimi (funding nakdi + basis degisimi, yil bazinda)
    df = pd.DataFrame({"date": p["date"], "f": f_by_bar, "b": np.r_[0.0, np.diff(P - S)]})
    df["y"] = df["date"].dt.year
    for y, g in df.groupby("y"):
        yy = str(y) if y != 2023 else "2023H1"
        out["regimes"][yy] = {"funding_usd": round(float(g["f"].sum()), 1),
                              "basis_chg_usd": round(float(g["b"].sum()), 1),
                              "n_hours": int(len(g))}
    # gunluk net seri (vol/MaxDD tanimsal)
    dd = df.set_index("date").resample("1D").agg({"f": "sum", "b": "sum"})
    dd["net"] = dd["f"] + dd["b"]
    eq = dd["net"].cumsum()
    out["daily"] = {"n_days": int(len(dd)),
                    "maxdd_usd": round(float(-(eq - eq.cummax()).min()), 1),
                    "vol_daily_usd": round(float(dd["net"].std(ddof=1)), 2)}
    print(f"ledger total: ${total:,.1f} | rejimler: {list(out['regimes'])}", flush=True)
    out["elapsed_min"] = round((time.time() - t0) / 60, 1)
    with open(D9 / "PREFLIGHT.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)
    for kk, vv in out["scenarios"].items():
        print(f"{kk}: {vv}", flush=True)


if __name__ == "__main__":
    main()
