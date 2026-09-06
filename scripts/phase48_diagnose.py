"""Phase 4.8 diagnosis — READ-ONLY (eğitim yok, tuning yok, Final B yok).

Girdiler: tuning47/run_*.json, art_*.json, diag_*.jsonl (mevcut artifact'lar) +
BTC feather (salt-okunur fiyat okuma) + env kodu (statik referans).
Yöntem notu: replay, env transition kurallarını birebir uygular; forced-close
fiyatı son mumdur (Phase 4/4.7 kayıtlarındaki 1-mumluk forced exit fiyat
yaklaşımından AYRILIR — bulgu #7; equity/reward etkilenmez, env tarafı exact).
Çıktı: tuning47/diag48.json + stdout tabloları.
"""
import glob
import json
import pathlib

ROOT = pathlib.Path(__file__).parents[1]
import pandas as pd

D47 = ROOT / "experiments" / "phase_04_rl" / "tuning47"
FEE, SLIP = 0.001, 0.0005
SEEDS = [42, 7, 123, 2026, 999]
VAL_START = pd.Timestamp("2023-01-01")


def load_runs():
    runs = {}
    for p in sorted(glob.glob(str(D47 / "run_E*.json"))):
        r = json.load(open(p, encoding="utf-8"))
        runs.setdefault(r["config"], {})[r["seed"]] = r
    return runs


def val_frame():
    df = pd.read_feather(ROOT / "freqtrade/user_data/data/binance/BTC_USDT-5m.feather")
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df.sort_values("date").reset_index(drop=True)
    v = df[(df["date"] >= "2023-01-01") & (df["date"] <= "2023-06-30")].reset_index(drop=True)
    return v


def replay(actions, closes, window=30):
    """Env transition replay: flat+BUY->aç, long+SELL->kapat, sonda long->forced.
    Dönüş: trades [(open_idx, close_idx, open_px, close_px, forced:bool)]."""
    pos, entry = False, None
    trades = []
    n = len(actions)
    for k, a in enumerate(actions):
        ci = window + k  # env t kayması (phase47_aggregate'de doğrulandı)
        if not pos and a == 1:
            pos, entry = True, (ci, closes[ci])
        elif pos and a == 2:
            trades.append((entry[0], ci, entry[1], closes[ci], False))
            pos, entry = False, None
    if pos:
        trades.append((entry[0], len(closes) - 1, entry[1], closes[len(closes) - 1], True))
    return trades


def trade_pnl(o, c, stake=100.0):
    amount = stake * (1 - FEE) / (o * (1 + SLIP))
    proceeds = amount * c * (1 - SLIP) * (1 - FEE)
    gross = amount * (c - o)
    fee = stake * FEE + amount * c * (1 - SLIP) * FEE
    return proceeds - stake, gross, fee


def main():
    runs = load_runs()
    vdf = val_frame()
    closes = vdf["close"].values
    assert len(vdf) - 30 - 1 == 51794, len(vdf)  # action sayısı tutarlılığı
    out = {"E1": {}, "scatter": [], "gates_invalid": {}, "diag": {},
           "buy_hold_ref": None, "zero_class": [], "forced_check": {}}

    # --- E1 deep-dive ---
    for s in SEEDS:
        a = json.load(open(D47 / f"art_E1_seed{s}.json", encoding="utf-8"))
        acts = a["actions"]
        assert len(acts) == 51794
        trades = replay(acts, closes)
        pnls = []
        for o_i, c_i, o, c, forced in trades:
            # all-in stake zinciri (env ile aynı): stake = o ana kadarki equity
            pnls.append((o_i, c_i, o, c, forced))
        # P&L'i env sırasıyla (stake = önceki equity)
        eq, enriched = 100.0, []
        for o_i, c_i, o, c, forced in pnls:
            p, g, f = trade_pnl(o, c, eq)
            enriched.append({"open_idx": o_i, "close_idx": c_i, "forced": forced,
                             "net": round(p, 3), "stake": round(eq, 2)})
            eq += p
        # sadakat: replay net == kayıtlı net (tolerans: forced 1-mum farkı HARİÇ tutulamaz,
        # bu yüzden karşılaştırma env-equity eğrisine karşı yapılır)
        art_eq = json.load(open(D47 / f"art_E1_seed{s}.json", encoding="utf-8"))["equities"]
        out["E1"][str(s)] = {
            "n_replay": len(enriched),
            "n_recorded": runs["E1"][s]["val"]["trade_count"],
            "replay_net": round(sum(e["net"] for e in enriched), 3),
            "recorded_net": runs["E1"][s]["val"]["net_abs"],
            "env_final_equity": round(art_eq[-1], 3),
            "trades": enriched,
            "holds_min": sorted((e["close_idx"] - e["open_idx"]) * 5 for e in enriched),
        }
        # konsantrasyon: en büyük 3 trade'in payı
        nets = sorted((float(e["net"]) for e in enriched), reverse=True)
        tot = sum(nets)
        out["E1"][str(s)]["top3_share"] = round(float(sum(nets[:3]) / tot), 3) if tot else 0.0
    # forced doğrulaması: replay equity == env equity eğrisi sonu
    for s in SEEDS:
        e = out["E1"][str(s)]
        ok = bool(abs((100.0 + e["replay_net"]) - e["env_final_equity"]) < 0.5)
        out["forced_check"][str(s)] = {"match_env_equity": ok, "trades": e["n_replay"]}
    print("E1 replay vs kayıt:", {s: (out["E1"][str(s)]["n_replay"], out["E1"][str(s)]["recorded_net"],
          out["E1"][str(s)]["replay_net"], out["E1"][str(s)]["top3_share"]) for s in SEEDS}, flush=True)
    print("forced-check:", out["forced_check"], flush=True)

    # --- scatter: Sharpe vs n (40 koşu, kayıtlı metrikler) ---
    for cid in sorted(runs):
        for s in SEEDS:
            v = runs[cid][s]["val"]
            out["scatter"].append({"config": cid, "seed": s, "n": v["trade_count"],
                                   "sharpe": v["daily_sharpe"], "net": v["net_abs"]})
    import statistics
    small = [p for p in out["scatter"] if 0 < p["n"] <= 20]
    print("n<=20 koşu Sharpe'ları:", sorted((p["sharpe"], p["config"], p["seed"], p["n"]) for p in small), flush=True)
    zero = [p for p in out["scatter"] if p["n"] == 0]
    print(f"zero-trade koşu: {len(zero)}/40", flush=True)

    # --- invalid oranları (kayıtlı gate stringleri) ---
    for cid in sorted(runs):
        rates = []
        for s in SEEDS:
            for h in runs[cid][s]["gates"]["hard_fails"]:
                if h.startswith("invalid action"):
                    rates.append(float(h.split("%")[1].split()[0]))
        out["gates_invalid"][cid] = {"n": len(rates), "min": min(rates), "max": max(rates),
                                     "mean": round(sum(rates) / len(rates), 1)} if rates else {}
    print("invalid% (config):", {c: out["gates_invalid"][c].get("mean") for c in sorted(out["gates_invalid"])}, flush=True)

    # --- diag: config içi eğitim-boyu aksiyon evrimi (E1 vs diğerleri, seed42) ---
    for cid in ["E0", "E1", "E4", "E7"]:
        try:
            rows = [json.loads(x) for x in
                    open(D47 / f"diag_{cid}_seed42.jsonl", encoding="utf-8").read().strip().split("\n")]
        except FileNotFoundError:
            continue
        first = rows[0]["actions"]
        last = rows[-1]["actions"]
        tot0, tot1 = sum(first.values()), sum(last.values())
        ent = [r.get("log_train/entropy_loss") for r in rows if "log_train/entropy_loss" in r]
        out["diag"][cid] = {"rollouts": len(rows),
                            "first_buy_share": round(first.get("1", 0) / max(1, tot0), 3),
                            "last_buy_share": round(last.get("1", 0) / max(1, tot1), 3),
                            "mean_entropy_loss": round(sum(ent) / len(ent), 4) if ent else None}
    print("diag:", out["diag"], flush=True)

    # --- buy-and-hold aritmetik referans (backtest DEĞİL) ---
    o = float(vdf["close"].iloc[0])
    c = float(vdf["close"].iloc[-1])
    bh_gross = (c - o) / o
    bh_net = (1 - FEE) * (c * (1 - SLIP)) / (o * (1 + SLIP)) - 1
    out["buy_hold_ref"] = {"open": o, "close": c, "gross_pct": round(bh_gross * 100, 2),
                           "net_pct_costly": round(bh_net * 100, 2)}
    print("buy-hold ref:", out["buy_hold_ref"], flush=True)

    json.dump(out, open(D47 / "diag48.json", "w", encoding="utf-8"), indent=2)
    print("yazıldı: diag48.json", flush=True)


if __name__ == "__main__":
    main()
