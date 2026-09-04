"""
Faz 2/3/5 — Backtest değerlendirmesi: Sharpe/Sortino/MaxDD/Profit Factor
+ FDR düzeltmesi + Type II (power/effect size) raporu.
"""
import pandas as pd, numpy as np, pathlib, json
from src.data.metrics import sharpe, sortino, max_drawdown, profit_factor
from statsmodels.stats.multitest import multipletests

def evaluate_trades(trades_csv: str):
    df=pd.read_csv(trades_csv) if pathlib.Path(trades_csv).exists() else pd.DataFrame()
    if df.empty:
        print("trade csv yok/boş")
        return {}
    # DÜZELTME 2026-09-04: Eski bug `profit_ratio` (per-trade) doğrudan `sqrt(365)` ile şişiyordu (6.02).
    # Doğru: Sharpe günlük return üzerinden annualize edilmeli (kripto 365).
    # Kaynak: `src/data/metrics.py:5` `periods_per_year=365` sadece günlük için doğru.
    # Yöntem: close_date varsa günlük aggregate (sum profit_ratio per day, 0-filled), yoksa
    # trades_per_year ile per-trade annualization.
    if "profit_ratio" in df.columns and "close_date" in df.columns:
        try:
            df["close_date"] = pd.to_datetime(df["close_date"])
            df["date"] = df["close_date"].dt.date
            daily = df.groupby("date")["profit_ratio"].sum()
            # takvim günleri 0 ile doldur (trade olmayan gün = 0 return)
            full_idx = pd.date_range(daily.index.min(), daily.index.max(), freq="D").date
            daily_full = pd.Series(0.0, index=full_idx)
            daily_full.update(daily)
            sharpe_val = sharpe(daily_full, periods_per_year=365)
            sortino_val = sortino(daily_full, periods_per_year=365)
            equity_daily = (1 + daily_full).cumprod()
            max_dd_val = max_drawdown(equity_daily)
            res=dict(
                sharpe=sharpe_val,
                sortino=sortino_val,
                max_dd=max_dd_val,
                profit_factor=profit_factor(df) if "profit_ratio" in df.columns else 0,
                n_trades=len(df),
                n_days=len(daily_full),
                method="daily_365",
            )
            print(json.dumps(res, indent=2))
            return res
        except Exception as e:
            print(f"[evaluate] daily fallback failed: {e}")
    # Fallback: per-trade ama trades_per_year ile (eski 365 değil)
    returns = df["profit_ratio"].fillna(0) if "profit_ratio" in df.columns else pd.Series([0])
    # trades_per_year hesabı (doğru annualization)
    try:
        if "close_date" in df.columns and len(df) > 1:
            d0 = pd.to_datetime(df["close_date"].iloc[0])
            d1 = pd.to_datetime(df["close_date"].iloc[-1])
            days = max(1, (d1 - d0).days + 1)
            tpy = len(returns) / (days / 365)
        else:
            tpy = 365
        sharpe_val = sharpe(returns, periods_per_year=int(tpy))
        sortino_val = sortino(returns, periods_per_year=int(tpy))
    except:
        sharpe_val = sharpe(returns, periods_per_year=365)
        sortino_val = sortino(returns, periods_per_year=365)
    equity = (1+returns).cumprod()
    res=dict(
        sharpe=sharpe_val,
        sortino=sortino_val,
        max_dd=max_drawdown(equity),
        profit_factor=profit_factor(df) if "profit_ratio" in df.columns else 0,
        n_trades=len(df),
        method="per_trade_tpy",
    )
    print(json.dumps(res, indent=2))
    return res

def fdr_correct(pvals, alpha=0.05):
    rej, p_corr, *_ = multipletests(pvals, alpha=alpha, method="fdr_bh")
    return rej, p_corr

def cohens_d(a,b):
    a=np.asarray(a); b=np.asarray(b)
    pooled=np.sqrt((a.var(ddof=1)+b.var(ddof=1))/2)
    return (a.mean()-b.mean())/pooled if pooled!=0 else 0.0

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--trades", default="user_data/backtest_results/trades.csv")
    args=p.parse_args()
    evaluate_trades(args.trades)
