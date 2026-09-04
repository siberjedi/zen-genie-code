"""Faz 3 — Baseline karşılaştırması + kilitli eşik kontrolü (tanım, sonuç yok).

- Birincil karşılaştırma (deneyde): FreqAI validation Sharpe - Baseline validation
  Sharpe (aynı pencere/universe/maliyet). İkincil: Faz 2 aggregate referansı.
- Eşikler `config/experiment.yaml:57-61`den okunur; bu modül ASLA değiştirmez.
- "Anlamlı fark yok" != "edge yok": effect size + power raporlanır.
"""
import yaml
import pathlib

ROOT = pathlib.Path(__file__).parents[2]
THRESH_PATH = ROOT / "config" / "experiment.yaml"

# Faz 2 aggregate referansı (bağlam için; birincil karşılaştırma validation penceresidir)
BASELINE_OOS_SHARPE_AGG = -1.807
BASELINE_MEDIAN_FOLD_SHARPE = -1.684


def load_thresholds() -> dict:
    cfg = yaml.safe_load(THRESH_PATH.read_text(encoding="utf-8"))
    return cfg["thresholds"]["phase_03_freqai"]


def sharpe_delta(freqai_sharpe: float, baseline_sharpe: float) -> float:
    return float(freqai_sharpe) - float(baseline_sharpe)


def check_thresholds(delta: float, wf_win_rate: float, max_dd: float,
                     seed_std: float) -> dict:
    """Kilitli eşiklere karşı kontrol (salt-okunur)."""
    th = load_thresholds()
    checks = {
        "sharpe_delta>=0.30": delta >= th["min_sharpe_delta_vs_baseline"],
        "wf_win_rate>=0.60": wf_win_rate >= th["min_wf_win_rate_vs_baseline"],
        "maxdd<=0.20": abs(max_dd) <= th["max_drawdown"],
        "seed_std<0.25": seed_std < 0.25,
    }
    checks["ALL_PASS"] = all(checks.values())
    return {"thresholds": th, "checks": checks}
