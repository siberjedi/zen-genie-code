"""Faz 4.4 — Run failure gates (teşhis amaçlı; strateji eşiği DEĞİL).

Hard-fail = pipeline/run geçersiz. Warning = dikkat, sonuç yorumlanırken bakılır.
Eşiklerin hiçbiri trading kuralı değildir; çoğu Phase 2/3'te ÖLÇÜLMÜŞ
referanslara (turnover 4.0/gün baseline, 86.7/gün FreqAI) göre betimseldir.
"""
import math

import numpy as np


def check_run(metrics: dict) -> dict:
    """metrics beklenen anahtarlar: trade_count, actions{0,1,2}, invalid_actions,
    total_steps, bankruptcy:bool, nan_reward:bool, obs_var:float, fees_paid:float,
    gross_profit:float, max_dd:float|None, timed_out:bool, exception:str|None."""
    hard, warn = [], []
    n = max(1, int(metrics.get("total_steps", 0)))
    if metrics.get("exception"):
        hard.append(f"exception: {metrics['exception']}")
    if metrics.get("timed_out"):
        hard.append("timeout (12h cap)")
    if metrics.get("nan_reward"):
        hard.append("NaN reward")
    if metrics.get("bankruptcy"):
        hard.append("bankruptcy (truncated)")
    inv_rate = float(metrics.get("invalid_actions", 0)) / n
    if inv_rate > 0.01:
        hard.append(f"invalid action %{inv_rate * 100:.2f} > %1")
    if float(metrics.get("obs_var", 1.0)) == 0.0:
        hard.append("constant observation (varyans 0)")
    acts = metrics.get("actions", {})
    n_tr = int(metrics.get("trade_count", 0))
    if n_tr == 0:
        warn.append("zero-trade")
    if acts.get(1, 0) == 0 and acts.get(2, 0) == 0:
        warn.append("only-HOLD")
    if acts.get(1, 0) > 0 and acts.get(2, 0) == 0:
        warn.append("BUY var + SELL yok (öğrenilmemiş çıkış)")
    tpd = n_tr / max(1, float(metrics.get("n_days", 1)))
    if tpd > 3 * 86.7:
        warn.append(f"excessive turnover ({tpd:.1f}/gün > 3x Phase-3 86.7)")
    if float(metrics.get("fees_paid", 0)) > float(metrics.get("gross_profit", 0)) > 0:
        warn.append("fee > gross (fee ölümü)")
    if metrics.get("max_dd") is None and n_tr > 0:
        warn.append("undefined MaxDD")
    return {"hard_fails": hard, "warnings": warn,
            "pass": not hard, "trades_day": round(tpd, 2)}
