"""Primary: OOS Sharpe, secondary metrikler — tek kaynak.

DÜZELTME 2026-09-04 (Phase 1 → 2):
- Eski bug: per-trade `profit_ratio` serisi doğrudan `periods_per_year=365` ile annualize ediliyordu
  → `src/backtest/evaluate.py:15` `returns = df["profit_ratio"]` + `sharpe(returns)` ve
    `dashboard/backend/app.py:893` `rets=[close_profit]` + `sqrt(365)` şişirme (6.02).
  Trade frekansı ≠ günlük frekans; `365` sadece **günlük** return için doğru.
- Doğru: Sharpe `günlük` return üzerinden `sqrt(365)` ile hesaplanmalı.
  Per-trade seri için `trades_per_year = n_trades / (gün_sayısı/365)` kullanılmalı.
  Bu dosya **değişmedi** (imza aynı, primary metric aynı), sadece dokümantasyon + doğruluk notu eklendi;
  asıl fix `evaluate.py` ve `dashboard app.py`'de günlük return'e çevrildi.
- `rf` yıllık risk-free; per-period `rf/periods` çıkarılır (rf=0 iken etkisiz).
"""
import numpy as np
import pandas as pd

def sharpe(returns: pd.Series, rf: float = 0.0, periods_per_year: int = 365) -> float:
    """OOS Sharpe — `returns` per-period olmalı.
    Kripto günlük için `periods_per_year=365`, per-trade için `trades_per_year` geçin.
    Eski 6.02 değeri per-trade+365 ile şişmişti, artık güvenilir değil."""
    excess = returns - rf / periods_per_year
    if excess.std() == 0:
        return 0.0
    return float(excess.mean() / excess.std() * np.sqrt(periods_per_year))

def sortino(returns: pd.Series, rf: float = 0.0, periods_per_year: int = 365) -> float:
    """Sortino — downside sadece negatif per-period return'ler üzerinden."""
    excess = returns - rf / periods_per_year
    downside = excess[excess < 0].std()
    if downside == 0 or np.isnan(downside):
        return float("inf") if excess.mean() > 0 else 0.0
    return float(excess.mean() / downside * np.sqrt(periods_per_year))

def max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    dd = (equity - roll_max) / roll_max
    return float(dd.min())

def profit_factor(trades: pd.DataFrame, pnl_col: str = "profit_ratio") -> float:
    wins = trades.loc[trades[pnl_col] > 0, pnl_col].sum()
    losses = -trades.loc[trades[pnl_col] < 0, pnl_col].sum()
    if losses == 0:
        return float("inf") if wins > 0 else 0.0
    return float(wins / losses)
