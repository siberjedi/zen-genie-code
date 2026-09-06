"""Phase 4.11 karşılaştırma — READ-ONLY analiz + deterministik replay (eğitim YOK).

- B run JSON'ları + A (tuning47) run JSON'ları → medyan/mean/delta/Mann-Whitney/Cohen d.
- Kayıtlı B modellerinden deterministik replay (inference-only) → forced/non-forced
  ayrımı + hold istatistikleri. Final B YOK.
Çıktı: pilot411/comparison411.json (küçük) + stdout.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from sb3_contrib import MaskablePPO

from src.rl.env import TradingEnv
from src.rl.train import load_rl_data, load_experiment_config

RES = ROOT / "experiments" / "phase_04_rl" / "pilot411"
ARES = ROOT / "experiments" / "phase_04_rl" / "tuning47"
MODELDIR = ROOT / "freqtrade" / "user_data" / "rl_models" / "phase411"
SEEDS = [42, 7, 123, 2026, 999]
FEE, SLIP = 0.001, 0.0005


def load_runs(d, prefix):
    out = {}
    for p in sorted(pathlib.Path(d).glob(f"run_{prefix}*.json")):
        r = json.load(open(p, encoding="utf-8"))
        out.setdefault(r["config"], {})[r["seed"]] = r
    return out


def replay_forced(config_id, seed, va_n, raw_close, raw_dates):
    """Dondurulmuş modelden deterministik replay → forced/non-forced ayrımı.
    Obs normalize, fiyatlar HAM (ekonomi ham fiyatla; normalize ile karıştırma!)."""
    model = MaskablePPO.load(str(MODELDIR / f"p411_{config_id}_seed{seed}.zip"))
    env = TradingEnv(va_n, price_col="close_raw")
    obs, _ = env.reset(seed=9999)
    cur, trades = None, []
    prev_eq = 100.0
    done = False
    while not done:
        mask = env.action_masks()
        action, _ = model.predict(obs, action_masks=mask, deterministic=True)
        action = int(action)
        assert bool(mask[action]), "maske ihlali (replay)"
        obs, _, term, trunc, info = env.step(action)
        ci = env.t - 1
        if cur is None and info["position"] == 1:
            cur = {"open_idx": ci, "open": raw_close[ci], "stake": prev_eq}
        if cur is not None and info["position"] == 0:
            fforced = bool(term and info.get("forced_close"))
            fci = len(raw_close) - 1 if fforced else ci
            stake = cur["stake"]
            amount = stake * (1 - FEE) / (cur["open"] * (1 + SLIP))
            proceeds = amount * raw_close[fci] * (1 - SLIP) * (1 - FEE)
            trades.append({"forced": fforced, "net": proceeds - stake,
                           "hold_min": (fci - cur["open_idx"]) * 5})
            cur = None
        prev_eq = info["equity"]
        done = term or trunc
    return trades


def main():
    B = load_runs(RES, "")
    A = load_runs(ARES, "")
    a_all = [A[c][s]["val"]["daily_sharpe"] for c in A for s in SEEDS]
    e1 = [A["E1"][s]["val"]["daily_sharpe"] for s in SEEDS]
    out = {"A_pool": {"n": len(a_all), "median": float(np.median(a_all)),
                      "mean": float(np.mean(a_all))},
           "E1_mirror": {"median": float(np.median(e1)), "mean": float(np.mean(e1))}}
    print("A pool (n=%d): median=%+.3f mean=%+.3f" % (len(a_all), out["A_pool"]["median"], out["A_pool"]["mean"]), flush=True)
    print("E1 mirror: median=%+.3f mean=%+.3f" % (out["E1_mirror"]["median"], out["E1_mirror"]["mean"]), flush=True)
    cfg_exp = load_experiment_config()
    val_df = load_rl_data("BTC/USDT", "2023-01-01", "2023-06-30", "validation", cfg_exp)
    val_df["close_raw"] = val_df["close"].values
    from src.rl.normalize import FitNormalizer
    tr_df = load_rl_data("BTC/USDT", "2020-01-01", "2022-12-31", "train", cfg_exp)
    nz = FitNormalizer(["close", "volume"]).fit(tr_df, "2020-01-01->2022-12-31")
    va_n = nz.transform(val_df)
    va_n["close_raw"] = val_df["close_raw"].values
    comp = {}
    for cid in ["B1", "B2"]:
        sh = [B[cid][s]["val"]["daily_sharpe"] for s in SEEDS]
        nets = [B[cid][s]["val"]["net_abs"] for s in SEEDS]
        ns = [B[cid][s]["val"]["trade_count"] for s in SEEDS]
        try:
            from scipy.stats import mannwhitneyu
            _, p_pool = mannwhitneyu(sh, a_all, alternative="two-sided")
            _, p_e1 = mannwhitneyu(sh, e1, alternative="two-sided")
        except Exception as e:
            p_pool = p_e1 = f"err:{e}"
        import math
        m1, m2 = float(np.mean(sh)), float(np.mean(a_all))
        s1, s2 = (float(np.std(sh, ddof=1)) if len(set(sh)) > 1 else 0.0,
                  float(np.std(a_all, ddof=1)))
        pooled = math.sqrt((s1 ** 2 + s2 ** 2) / 2) if (s1 or s2) else 0.0
        d = (m1 - m2) / pooled if pooled else 0.0
        # forced ayrımı (replay)
        fall, fnf, ffo = [], [], []
        raw_close_arr = val_df["close"].values
        raw_dates_arr = pd.to_datetime(val_df["date"]).reset_index(drop=True)
        for s in SEEDS:
            tr = replay_forced(cid, s, va_n, raw_close_arr, raw_dates_arr)
            for t in tr:
                (ffo if t["forced"] else fnf).append(t["net"])
            fall.extend(tr)
        # hold medyanı run metriklerinden (kayıtlı)
        holds_med = [B[cid][s]["val_med_hold_min"] for s in SEEDS]
        comp[cid] = {"sharpes": sh, "median": float(np.median(sh)), "mean": m1,
                     "nets": nets, "ns": ns,
                     "delta_median_pool": float(np.median(sh) - out["A_pool"]["median"]),
                     "delta_mean_pool": round(m1 - out["A_pool"]["mean"], 4),
                     "delta_median_e1": round(float(np.median(sh)) - out["E1_mirror"]["median"], 4),
                     "mannwhitney_p_pool": p_pool, "mannwhitney_p_e1": p_e1,
                     "cohens_d_vs_pool": round(d, 3),
                     "forced_trades": len(ffo), "forced_net": round(sum(ffo), 2),
                     "nonforced_trades": len(fnf), "nonforced_net": round(sum(fnf), 2),
                     "total_net": round(sum(fnf) + sum(ffo), 2)}
        print("%s: median=%+.3f mean=%+.3f d_med_pool=%+.3f d_med_e1=%+.3f p_pool=%s p_e1=%s d=%+.3f" % (
            cid, comp[cid]["median"], m1, comp[cid]["delta_median_pool"],
            comp[cid]["delta_median_e1"], str(p_pool)[:8], str(p_e1)[:8], comp[cid]["cohens_d_vs_pool"]), flush=True)
        print("   forced: %d trade net=%+.2f | nonforced: %d trade net=%+.2f | holds_med=%s" % (
            len(ffo), sum(ffo), len(fnf), sum(fnf), holds_med), flush=True)
    out["comparison"] = comp
    json.dump(out, open(RES / "comparison411.json", "w", encoding="utf-8"), indent=2)
    print("yazıldı: comparison411.json", flush=True)


if __name__ == "__main__":
    main()
