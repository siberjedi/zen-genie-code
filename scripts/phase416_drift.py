"""Phase 4.16 — EXPOSURE / DRIFT ATTRIBUTION TEST (READ-ONLY).

Training YOK, tuning YOK, model/env/reward değişikliği YOK, Final B YOK.

Soru: "E1 RL'nin pozitif görünen performansının ne kadarı gerçek karar
kalitesinden, ne kadarı BTC'nin validation yükselişinden?"

Referanslar (mevcut val verisi, env-birebir fee/slip/execution):
A) BUY & HOLD        — candle 30'da long, son mumda kapanış.
B) BULL EXPOSURE     — günlük rejim=bull iken long (kilitli Şph02 classifier).
C) IMMEDIATE RE-ENTRY— RL valid SELL'lerini kullan, SELL mumunu takip eden ilk
                        uygun mumda tekrar BUY (exposure'u izole eder).
D) RL E1 5 seed      — kayıtlı artifact'lar.

Metrikler: scripts.phase03_experiment.metrics_from_trades BİREBİR (RL ile aynı
fonksiyon). Exposure = tradable mumlarda (candle 30..son) long kalma oranı.
Çıktı: tuning47/drift416.json + stdout tabloları.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from scripts.phase02_analyze import compute_regime
from scripts.phase03_experiment import metrics_from_trades

D47 = ROOT / "experiments" / "phase_04_rl" / "tuning47"
SEEDS = [42, 7, 123, 2026, 999]
FEE, SLIP = 0.001, 0.0005
VAL_START, VAL_END = "2023-01-01", "2023-06-30"
TRADE_KEYS = ("pair", "open_date", "close_date", "open_rate", "close_rate",
              "stake_amount", "profit_abs", "profit_ratio")


def load_val():
    df = pd.read_feather(ROOT / "freqtrade/user_data/data/binance/BTC_USDT-5m.feather")
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)
    v = df[(df["date"] >= VAL_START) & (df["date"] <= VAL_END)].reset_index(drop=True)
    return df, v


def collapse(r):
    if r.startswith("bull"):
        return "bull"
    if r.startswith("bear"):
        return "bear"
    return r


def candle_regimes(full, vdf):
    d = full.set_index("date").resample("1D").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    d = d.dropna()
    reg = compute_regime(d.copy())["regime"]
    day2reg = {k.date(): collapse(v) for k, v in reg.items()}
    vdf["day"] = vdf["date"].dt.date
    vdf["creg"] = vdf["day"].map(day2reg)
    return vdf["creg"].values


def simulate(actions, closes, reward_from_actions=True):
    """Genel state-machine simülasyonu.

    actions: her candle için [BUY/SELL/None] karar listesi (None = hiçbir şey).
    Kurallar (env birebir): flat iken BUY -> close*(1+slip), stake*(1-fee);
    long iken SELL -> close*(1-slip)*(1-fee). Pencere sonu açıksa forced close.
    Dönüş: trades (+ fee/slip/gross), pre_pos listesi (exposure).
    """
    trades, pre_pos, pos, eq = [], [], False, 100.0
    entry = None
    n = len(closes)
    for c in range(30, n - 1):
        k = c - 30
        a = actions[k] if k < len(actions) else None
        pre_pos.append(1 if pos else 0)
        if not pos and a == "B":
            cp = closes[c] * (1 + SLIP)
            amt = eq * (1 - FEE) / cp
            entry = {"c": c, "close": closes[c], "amt": amt, "stake": eq}
            pos = True
        elif pos and a == "S":
            o = entry
            proceeds = o["amt"] * closes[c] * (1 - SLIP) * (1 - FEE)
            fee = o["stake"] * FEE + o["amt"] * closes[c] * (1 - SLIP) * FEE
            slip = o["amt"] * SLIP * (o["close"] + closes[c])
            trades.append({"open_idx": o["c"], "close_idx": c, "forced": False,
                           "open": o["close"], "close": closes[c], "stake": o["stake"],
                           "profit": proceeds - o["stake"], "fee": fee, "slip": slip,
                           "gross": o["amt"] * (closes[c] - o["close"])})
            eq += proceeds - o["stake"]
            pos = False
    if pos and entry is not None:
        c = n - 1
        o = entry
        proceeds = o["amt"] * closes[c] * (1 - SLIP) * (1 - FEE)
        fee = o["stake"] * FEE + o["amt"] * closes[c] * (1 - SLIP) * FEE
        slip = o["amt"] * SLIP * (o["close"] + closes[c])
        trades.append({"open_idx": o["c"], "close_idx": c, "forced": True,
                       "open": o["close"], "close": closes[c], "stake": o["stake"],
                       "profit": proceeds - o["stake"], "fee": fee, "slip": slip,
                       "gross": o["amt"] * (closes[c] - o["close"])})
        eq += proceeds - o["stake"]
        pos = False
    return trades, pre_pos, eq


def to_metric_trades(trades, dates):
    out = []
    for t in trades:
        out.append({"pair": "BTC/USDT",
                    "open_date": str(dates.iloc[t["open_idx"]])[:19],
                    "close_date": str(dates.iloc[t["close_idx"]])[:19],
                    "open_rate": round(t["open"], 6), "close_rate": round(t["close"], 6),
                    "stake_amount": round(t["stake"], 4),
                    "profit_abs": round(t["profit"], 4),
                    "profit_ratio": round(t["profit"] / t["stake"], 6)})
    return out


def summarize(label, trades, dates, closes, exposure_steps):
    mt = to_metric_trades(trades, dates)
    met = metrics_from_trades(mt, VAL_START, VAL_END) if mt else \
        {"trade_count": 0, "net_abs": 0.0, "daily_sharpe": 0.0, "sortino": 0.0,
         "max_dd": 0.0, "profit_factor": 0.0, "win_rate": 0.0, "turnover": 0,
         "total_volume": 0.0, "fee_est": 0.0}
    df = pd.DataFrame(trades)
    if len(df):
        holds = (df["close_idx"] - df["open_idx"]) * 5
        med_hold = round(float(holds.median()), 1) if len(holds) else 0.0
        gross = round(float(df["gross"].sum()), 3)
        fee = round(float(df["fee"].sum()), 3)
        slip = round(float(df["slip"].sum()), 3)
        wr = round(float((df["profit"] > 0).mean()), 4) if len(df) else 0.0
    else:
        med_hold = gross = fee = slip = 0.0
        wr = 0.0
    n_tradable = len(closes) - 31
    exposure = round(sum(exposure_steps) / n_tradable, 4)
    return {"label": label, "n_trades": len(trades),
            "net_abs": round(met["net_abs"], 3),
            "net_pct": round(met["net_abs"], 3),
            "gross": gross, "fee": fee, "slip": slip,
            "sharpe": met["daily_sharpe"], "sortino": met["sortino"],
            "max_dd": met["max_dd"], "pf": met["profit_factor"], "wr": wr,
            "turnover": met["turnover"], "volume": round(met["total_volume"], 1),
            "exposure": exposure, "med_hold_min": med_hold,
            "forced": int(df["forced"].sum()) if len(df) else 0}


def conc(rows, net):
    if not len(rows) or net == 0:
        return {"top1": None, "top3": None, "top5": None,
                "net_ex_top1": 0.0, "net_ex_top3": 0.0}
    prof = np.array([r["profit"] for r in rows])
    sorted_p = np.sort(prof)[::-1]
    top1, top3, top5 = (sorted_p[:1].sum(), sorted_p[:3].sum(), sorted_p[:5].sum())
    return {"top1": round(float(top1 / net), 4), "top3": round(float(top3 / net), 4),
            "top5": round(float(top5 / net), 4),
            "net_ex_top1": round(net - float(top1), 3),
            "net_ex_top3": round(net - float(top3), 3)}


def main():
    full, vdf = load_val()
    closes = vdf["close"].values.astype(float)
    dates = pd.to_datetime(vdf["date"]).reset_index(drop=True)
    assert len(closes) - 30 - 1 == 51794, len(closes)
    creg = candle_regimes(full, vdf.copy())
    n_tradable = len(closes) - 31
    out = {}

    # ---------- A) BUY & HOLD ----------
    act_bh = ["B"] + [None] * (len(closes) - 1 - 30)
    tr_bh, pre_bh, eq_bh = simulate(act_bh, closes)
    bh = summarize("buy_hold", tr_bh, dates, closes, pre_bh)
    out["buy_hold"] = bh
    out["bh_trades"] = to_metric_trades(tr_bh, dates)

    # ---------- B) BULL EXPOSURE ----------
    bull_actions, pos = [], False
    for c in range(30, len(closes) - 1):
        want = creg[c] == "bull"
        if not pos and want:
            bull_actions.append("B"); pos = True
        elif pos and not want:
            bull_actions.append("S"); pos = False
        else:
            bull_actions.append(None)
    tr_bull, pre_bull, eq_bull = simulate(bull_actions, closes)
    bull = summarize("bull_exposure", tr_bull, dates, closes, pre_bull)
    out["bull_exposure"] = bull
    out["bull_trades"] = to_metric_trades(tr_bull, dates)

    # ---------- C) IMMEDIATE RE-ENTRY (her RL seed) ----------
    reentry = {}
    for s in SEEDS:
        art = json.load(open(D47 / f"art_E1_seed{s}.json", encoding="utf-8"))
        acts = np.asarray(art["actions"])
        # RL valid pozisyon geçişlerini takip et; RE-ENTRY:
        # - RL valid BUY (flat->long) ile gir
        # - RL valid SELL (long->flat) ile çık, hemen SONRAKİ mumda tekrar BUY
        #   -> RL'nin SELL spam'leri (kendi flat dönemindeki invalid 2'ler) yeniden
        #      giriş tetiklemez; sadece gerçek pozisyon kapamaları kullanılır.
        act_final = []
        rl_was_long, we_long, pending = False, False, False
        for k in range(len(acts)):
            a = acts[k]
            rl_enter = (not rl_was_long) and a == 1
            rl_exit = rl_was_long and a == 2
            if rl_enter:
                rl_was_long = True
            if rl_exit:
                rl_was_long = False
            if not we_long and rl_enter:
                act_final.append("B"); we_long = True
            elif we_long and rl_exit:
                act_final.append("S"); we_long = False; pending = True
            elif pending:
                act_final.append("B"); we_long = True; pending = False
            else:
                act_final.append(None)
        # simulate() act_final'i 30+k indexinde okur -> len eşleşmeli
        tr_re, pre_re, eq_re = simulate(act_final, closes)
        re = summarize(f"reentry_{s}", tr_re, dates, closes, pre_re)
        re["conc"] = conc(tr_re, float(pd.DataFrame(tr_re)["profit"].sum()) if tr_re else 0.0)
        reentry[str(s)] = re
    out["reentry"] = reentry

    # ---------- D) RL E1 ----------
    rl = {}
    for s in SEEDS:
        art = json.load(open(D47 / f"art_E1_seed{s}.json", encoding="utf-8"))
        acts = np.asarray(art["actions"])
        pos = False; entry = None; eq = 100.0; trades = []; pre_pos = []
        for k, a in enumerate(acts):
            c = 30 + k
            pre_pos.append(1 if pos else 0)
            if not pos and a == 1:
                amt = eq * (1 - FEE) / (closes[c] * (1 + SLIP))
                entry = {"c": c, "close": closes[c], "amt": amt, "stake": eq}
                pos = True
            elif pos and a == 2:
                o = entry
                proceeds = o["amt"] * closes[c] * (1 - SLIP) * (1 - FEE)
                fee = o["stake"] * FEE + o["amt"] * closes[c] * (1 - SLIP) * FEE
                slip = o["amt"] * SLIP * (o["close"] + closes[c])
                gross = o["amt"] * (closes[c] - o["close"])
                trades.append({"open_idx": o["c"], "close_idx": c, "forced": False,
                               "open": o["close"], "close": closes[c], "stake": o["stake"],
                               "profit": proceeds - o["stake"], "fee": fee,
                               "slip": slip, "gross": gross})
                eq += proceeds - o["stake"]
                pos = False
        if pos:
            c = len(closes) - 1
            o = entry
            proceeds = o["amt"] * closes[c] * (1 - SLIP) * (1 - FEE)
            fee = o["stake"] * FEE + o["amt"] * closes[c] * (1 - SLIP) * FEE
            slip = o["amt"] * SLIP * (o["close"] + closes[c])
            trades.append({"open_idx": o["c"], "close_idx": c, "forced": True,
                           "open": o["close"], "close": closes[c], "stake": o["stake"],
                           "profit": proceeds - o["stake"], "fee": fee, "slip": slip,
                           "gross": o["amt"] * (closes[c] - o["close"])})
            eq += proceeds - o["stake"]
        r = summarize(f"rl_{s}", trades, dates, closes, pre_pos)
        r["conc"] = conc(trades, float(pd.DataFrame(trades)["profit"].sum()) if trades else 0.0)
        r["recon_final"] = round(eq, 3)
        r["saved_final"] = round(float(art["equities"][-1]), 3)
        rl[str(s)] = r
    out["rl"] = rl

    # ---------- Exposure / drift tablosu ----------
    bh_net = out["buy_hold"]["net_abs"] / 100.0          # net fraksiyon (fee+slip düşülmüş)
    bh_gross = out["buy_hold"]["gross"] / 100.0          # brüt fraksiyon (fee/slip HARİÇ)
    stride_min = n_tradable * 5
    out["regime_days"] = {}
    for c in range(len(creg)):
        out["regime_days"][str(dates.iloc[c].date())] = creg[c]
    from collections import Counter
    out["regime_day_counts"] = dict(Counter(out["regime_days"].values()))

    # referans stratejilerde de concentration (Bölüm 6)
    out["buy_hold"]["conc"] = conc(tr_bh, out["buy_hold"]["net_abs"])
    out["bull_exposure"]["conc"] = conc(tr_bull, out["bull_exposure"]["net_abs"])

    # ---------- Exposure normalization (Bölüm 4) ----------
    # Tanım: net_pct = net_abs/100 (başlangıç sermayesi bazlı).
    #  exposure = tradable mumlarda (candle 30..51823) long kalma fraksiyonu.
    #  net_per_exp = net_pct / exposure
    #  adj_net_pct  = net_pct − exposure × B&H_net_pct
    #                (aynı exposure ile 'sadece drift' net getirisinden kalan artık;
    #                 compounding + turnover fee'ler nedeniyle DESKRİPTİF, kesin değil)
    #  alpha_gross_pct = gross_pct − exposure × B&H_gross_pct
    #                (fee/slip netliği olmaksızın saf zamanlama artığı)
    norm = {}

    def add_norm(label, exposure, netpct, grosspct):
        in_market_min = round(exposure * stride_min)
        net_per_exp = round(netpct / exposure, 4) if exposure > 0 else None
        adj_net = round(netpct - exposure * bh_net, 4)
        alpha_gross = round(grosspct - exposure * bh_gross, 4)
        norm[label] = {"exposure": round(exposure, 4), "in_market_min": in_market_min,
                       "net_pct": round(netpct, 4), "gross_pct": round(grosspct, 4),
                       "net_per_exp": net_per_exp, "adj_net_pct": adj_net,
                       "alpha_gross_pct": alpha_gross}

    add_norm("buy_hold", out["buy_hold"]["exposure"], bh_net, bh_gross)
    add_norm("bull_exposure", out["bull_exposure"]["exposure"],
             out["bull_exposure"]["net_abs"] / 100.0, out["bull_exposure"]["gross"] / 100.0)
    for s in SEEDS:
        add_norm(f"rl_{s}", rl[str(s)]["exposure"], rl[str(s)]["net_abs"] / 100.0,
                 rl[str(s)]["gross"] / 100.0)
        add_norm(f"reentry_{s}", reentry[str(s)]["exposure"],
                 reentry[str(s)]["net_abs"] / 100.0, reentry[str(s)]["gross"] / 100.0)
    out["norm"] = norm

    exp_drift = {}
    rows = []
    for k, r in rl.items():
        exp = r["exposure"]
        rows.append({"seed": int(k), "exposure": exp, "net_pct": r["net_abs"] / 100.0})
        exp_drift[str(k)] = {"exposure": round(exp, 4),
                             "net_vs_reentry_delta": round(r["net_abs"] - reentry[str(k)]["net_abs"], 3),
                             "net_vs_bull_delta": round(r["net_abs"] - out["bull_exposure"]["net_abs"], 3),
                             **norm[f"rl_{k}"]}
    out["drift"] = exp_drift
    rd = pd.DataFrame(rows)
    if len(rd) > 1:
        spearman = rd["exposure"].corr(rd["net_pct"], method="spearman")
    else:
        spearman = None
    out["exposure_net_spearman"] = round(float(spearman), 4) if spearman is not None else None

    json.dump(out, open(D47 / "drift416.json", "w", encoding="utf-8"), indent=2, default=str)

    # ---------- stdout ----------
    def pr(r):
        print(f"  {r['label']:<22} n={r['n_trades']:>4}  net={r['net_abs']:>8.2f}  "
              f"gross={r['gross']:>8.2f}  fee={r['fee']:>7.2f} slip={r['slip']:>6.2f}  "
              f"Sh={r['sharpe']:>6.3f}  DD={r['max_dd']:>8.3f}  PF={r['pf']:>6.2f}  "
              f"WR={r['wr']:>5.3f}  exp={r['exposure']:>6.4f}  hold_med={r['med_hold_min']:>8.1f}")

    print("== A) BUY & HOLD =="); pr(bh)
    print("== B) BULL EXPOSURE =="); pr(bull)
    print("== C) IMMEDIATE RE-ENTRY (RL valid SELL + hemen tekrar BUY) ==")
    for s in SEEDS:
        pr(reentry[str(s)])
        print(f"      conc {reentry[str(s)]['conc']}")
    print("== D) RL E1 ==")
    for s in SEEDS:
        pr(rl[str(s)])
        print(f"      conc {rl[str(s)]['conc']}  recon={rl[str(s)]['recon_final']} vs saved={rl[str(s)]['saved_final']}")
    print(f"\nBuy&Hold: net={bh_net*100:.2f}% gross={bh_gross*100:.2f}%  |  "
          f"Regime days: {out['regime_day_counts']}")
    print("Exposure / drift (descriptive; beta = exposure × B&H):")
    for k, v in exp_drift.items():
        print(" ", k, {kk: vv for kk, vv in v.items() if kk != 'net_per_exp'})
    print("Exposure–net Spearman (5 RL seed, descriptive):", out["exposure_net_spearman"])
    print("Normalization (Bölüm 4):")
    for k, v in norm.items():
        print(" ", k, v)


if __name__ == "__main__":
    main()