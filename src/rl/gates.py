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


def action_breakdown(actions, positions) -> dict:
    """SADECE raporlama: valid/invalid aksiyon sınıflandırması (davranış DEĞİŞMEZ).

    actions[i]: o adımda seçilen aksiyon (0/1/2).
    positions[i]: aksiyon ÖNCESİ pozisyon durumu (0 flat / 1 long).
    Dönüş: her sınıfın sayısı + oranı. Invalid'ler ekonomik no-op'tur.
    """
    cats = {"valid_HOLD": 0, "valid_BUY": 0, "valid_SELL": 0,
            "invalid_SELL_while_flat": 0, "invalid_BUY_while_long": 0,
            "invalid_other": 0}
    for a, p in zip(actions, positions):
        if a == 0:
            cats["valid_HOLD"] += 1
        elif a == 1 and p == 0:
            cats["valid_BUY"] += 1
        elif a == 2 and p == 1:
            cats["valid_SELL"] += 1
        elif a == 2 and p == 0:
            cats["invalid_SELL_while_flat"] += 1
        elif a == 1 and p == 1:
            cats["invalid_BUY_while_long"] += 1
        else:
            cats["invalid_other"] += 1
    n = max(1, len(actions))
    out = dict(cats)
    out["rates"] = {k: round(v / n, 4) for k, v in cats.items()}
    out["invalid_total_rate"] = round(
        (cats["invalid_SELL_while_flat"] + cats["invalid_BUY_while_long"]
         + cats["invalid_other"]) / n, 4)
    return out


def sample_flag(n_trades: int) -> str:
    """SADECE raporlama etiketi (seçim kriteri DEĞİL):
    <10 EXTREME SMALL-N, 10-20 VERY SMALL-N, 20-50 SMALL-N, >=50 normal."""
    n = int(n_trades)
    if n < 10:
        return "EXTREME SMALL-N"
    if n < 20:
        return "VERY SMALL-N"
    if n < 50:
        return "SMALL-N"
    return "normal"
