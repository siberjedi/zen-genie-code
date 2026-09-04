"""
Faz 7 — X sinyalinin predictive power ölçümü.
Event → t+1m/5m/15m/1h piyasa davranışı.
Predictive power ≠ trading kârı — ayrı ölçülür, eşiği geçemezse X çıkarılır.
"""
import pandas as pd
import numpy as np

def event_study(events: pd.DataFrame, prices: pd.DataFrame, horizons=(1,5,15,60)):
    """events: timestamp, prices: timestamp+close"""
    res=[]
    for _, e in events.iterrows():
        t0=e["timestamp"]
        p0=prices.loc[prices["timestamp"]>=t0, "close"].iloc[0] if len(prices.loc[prices["timestamp"]>=t0]) else np.nan
        row={"event": e.get("text","")[:80]}
        for h in horizons:
            t1=t0+pd.Timedelta(minutes=h)
            p1=prices.loc[prices["timestamp"]>=t1, "close"].iloc[0] if len(prices.loc[prices["timestamp"]>=t1]) else np.nan
            row[f"ret_{h}m"]=(p1/p0-1) if p0 and p1 and not np.isnan(p1) else np.nan
        res.append(row)
    return pd.DataFrame(res)

def information_coefficient(signal: pd.Series, forward_ret: pd.Series):
    return signal.corr(forward_ret, method="spearman")
