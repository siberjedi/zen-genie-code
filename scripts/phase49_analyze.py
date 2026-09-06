"""Phase 4.9 E1 analizi — READ-ONLY (eğitim yok, tuning yok, Final B yok).

Girdi: tuning47/art_E1_{42,123,999}.json (kayıtlı aksiyon/equity/reward) +
BTC feather (tarih/fiyat, salt-okunur).
Yapar: exact replay (forced=sun mumu) + forced/non-forced partition +
cost split + small-N flag + reconciliation assertion'ları + invalid breakdown.
Çıktı: tuning47/partition_E1.json (küçük) + stdout tabloları.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from src.rl.gates import action_breakdown, sample_flag

D47 = ROOT / "experiments" / "phase_04_rl" / "tuning47"
FEE, SLIP = 0.001, 0.0005
SEEDS = [42, 123, 999]


def load_val():
    df = pd.read_feather(ROOT / "freqtrade/user_data/data/binance/BTC_USDT-5m.feather")
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)
    v = df[(df["date"] >= "2023-01-01") & (df["date"] <= "2023-06-30")].reset_index(drop=True)
    return v


def replay(actions, closes, dates):
    """Env transition replay (forced=sun mumu). Dönüş: trades + pre-position listesi.

    KRİTİK: aksiyon k, env-içi mum indeksi `off+k` ile eşleşir
    (off = len(closes)-len(actions)-1; val rollout'ta window=30). Tuning'deki
    `ci = env.t - 1` kuralıyla birebir aynı eşleme.
    """
    off = len(closes) - len(actions) - 1
    assert off >= 0, (len(closes), len(actions))
    pos, entry, stake = False, None, None
    eq = 100.0
    trades, pre_pos = [], []
    for k, a in enumerate(actions):
        ci = off + k
        pre_pos.append(1 if pos else 0)
        if not pos and a == 1:
            amount = eq * (1 - FEE) / (closes[ci] * (1 + SLIP))
            pos, entry, stake = True, (ci, closes[ci], amount, eq), eq
        elif pos and a == 2:
            o_k, o, amount, st = entry
            proceeds = amount * closes[ci] * (1 - SLIP) * (1 - FEE)
            fee = st * FEE + amount * closes[ci] * (1 - SLIP) * FEE
            slip = amount * SLIP * (o + closes[ci])
            trades.append({"open_idx": o_k, "close_idx": ci, "forced": False,
                           "open": o, "close": closes[ci], "stake": st,
                           "profit": proceeds - st, "fee": fee, "slip": slip,
                           "gross": amount * (closes[ci] - o)})
            eq += proceeds - st
            pos, entry, stake = False, None, None
    if pos:
        o_k, o, amount, st = entry
        k = len(closes) - 1  # forced: SON mum indeksi (kayıt uzayı)
        c = closes[-1]
        proceeds = amount * c * (1 - SLIP) * (1 - FEE)
        fee = st * FEE + amount * c * (1 - SLIP) * FEE
        slip = amount * SLIP * (o + c)
        trades.append({"open_idx": o_k, "close_idx": k, "forced": True,
                       "open": o, "close": c, "stake": st,
                       "profit": proceeds - st, "fee": fee, "slip": slip,
                       "gross": amount * (c - o)})
        eq += proceeds - st
    return trades, pre_pos, eq


def summarize(trades):
    import datetime
    df = pd.DataFrame(trades)
    if not len(df):
        return {"n": 0}
    df["hold_min"] = (df["close_idx"] - df["open_idx"]) * 5
    g = {}
    for name, sub in [("all", df), ("nonforced", df[~df["forced"]]),
                      ("forced", df[df["forced"]])]:
        if not len(sub):
            g[name] = {"n": 0}
            continue
        rets = sub["profit"] / sub["stake"]
        g[name] = {"n": int(len(sub)), "gross": round(float(sub["gross"].sum()), 2),
                   "fee": round(float(sub["fee"].sum()), 2),
                   "slip": round(float(sub["slip"].sum()), 2),
                   "net": round(float(sub["profit"].sum()), 2),
                   "wr": round(float((sub["profit"] > 0).mean()), 4),
                   "avg_ret": round(float(rets.mean()), 5),
                   "med_hold": round(float(sub["hold_min"].median()), 1),
                   "mean_hold": round(float(sub["hold_min"].mean()), 1),
                   "sample": sample_flag(len(sub))}
    return g


def main():
    vdf = load_val()
    closes = vdf["close"].values
    assert len(closes) - 30 - 1 == 51794, len(closes)  # aksiyon sayısı tutarlılığı
    out = {}
    for s in SEEDS:
        a = json.load(open(D47 / f"art_E1_seed{s}.json", encoding="utf-8"))
        acts = a["actions"]
        trades, pre_pos = replay(acts, closes, None)[:2]
        # trade ledger <-> equity + reward <-> equity reconciliation
        env_final = a["equities"][-1]
        assert abs(sum(t["profit"] for t in trades) - (env_final - 100.0)) < 0.05, \
            f"seed {s}: ledger/equity uyumsuz"
        assert abs(sum(a["rewards"]) - np.log(env_final / 100.0)) < 1e-9, \
            f"seed {s}: reward/equity uyumsuz"
        # invalid breakdown (davranış değişmez, sadece rapor)
        bd = action_breakdown(acts, pre_pos)
        # top-3 doğrulama
        nets = sorted((t["profit"] for t in trades), reverse=True)
        tot = sum(nets)
        top3 = round(sum(nets[:3]) / tot, 3) if tot else 0.0
        part = summarize(trades)
        # toplam reconciliation: forced + nonforced == all
        if part["forced"]["n"] and part["nonforced"]["n"]:
            assert abs((part["forced"]["net"] + part["nonforced"]["net"])
                       - part["all"]["net"]) < 0.01
        out[str(s)] = {"partition": part, "top3_share": top3,
                       "invalid": {k: bd[k] for k in
                                   ("invalid_SELL_while_flat", "invalid_BUY_while_long",
                                    "invalid_total_rate")},
                       "n_trades": len(trades)}
        p = part
        print(f"seed {s}: n={p['all']['n']} net={p['all']['net']} "
              f"[nonforced n={p['nonforced'].get('n',0)} net={p['nonforced'].get('net',0)} | "
              f"forced n={p['forced'].get('n',0)} net={p['forced'].get('net',0)}] "
              f"top3={top3} invalid={bd['invalid_total_rate']} "
              f"flag={p['all'].get('sample', sample_flag(p['all']['n']))}", flush=True)
    # E1 konfigürasyon özeti (kayıtlı val metriklerinden, değişiklik yok)
    json.dump(out, open(D47 / "partition_E1.json", "w", encoding="utf-8"), indent=2)
    print("yazıldı: partition_E1.json", flush=True)


if __name__ == "__main__":
    main()
