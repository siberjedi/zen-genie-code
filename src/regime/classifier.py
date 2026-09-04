"""
Mekanik rejim sınıflandırıcısı — hindsight yok (Anayasa Madde 9).
Kurallar experiment.yaml'da kilitli, sadece t'ye kadar veri kullanır.
"""
from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class RegimeConfig:
    sma_fast: int = 50
    sma_slow: int = 200
    adx_period: int = 14
    adx_threshold: float = 20.0
    atr_period: int = 14
    vol_lookback: int = 30
    vol_high_pct: float = 0.70
    vol_low_pct: float = 0.30

def classify(df: pd.DataFrame, cfg: RegimeConfig = RegimeConfig()) -> pd.Series:
    """df: OHLCV + hesaplanmış indikatörler. Sadece geçmişe bakar."""
    import talib.abstract as ta
    sma_fast = ta.SMA(df, timeperiod=cfg.sma_fast)
    sma_slow = ta.SMA(df, timeperiod=cfg.sma_slow)
    adx = ta.ADX(df, timeperiod=cfg.adx_period)
    atr = ta.ATR(df, timeperiod=cfg.atr_period)
    vol_rank = atr.rolling(cfg.vol_lookback).rank(pct=True)

    trend = pd.Series("sideways", index=df.index)
    trend[(sma_fast > sma_slow) & (adx > cfg.adx_threshold)] = "bull"
    trend[(sma_fast < sma_slow) & (adx > cfg.adx_threshold)] = "bear"

    vol = pd.Series("low_vol", index=df.index)
    vol[vol_rank > cfg.vol_high_pct] = "high_vol"
    # birleşik etiket: örn "bull_high_vol"
    return trend + "_" + vol
