"""Faz 3 — Kilitli feature set (sonuç öncesi kilitli, 2026-09-04).

Kurallar:
- SADECE geçmiş veri: her satırdaki feature yalnızca t ve öncesi mumları kullanır.
- Geleceğe kayan hiçbir op yok (`.shift(-n)`, ileriye dönük rolling yok).
- RSI: Wilder (TA-Lib ile aynı matematik; BaselineStrategy ile tutarlı).
- NaN politikası: warmup + kuyruk satırları ATILIR (doldurma yok).
"""
import pandas as pd
import numpy as np

FEATURES = [
    "ret_1",        # 1 mumluk getiri (t-1 -> t)
    "ret_12",       # 12 mumluk getiri (~1s, t-12 -> t)
    "rsi14",        # Wilder RSI(14)
    "sma50_ratio",  # close/SMA50 - 1
    "sma200_ratio", # close/SMA200 - 1
    "sma_trend",    # SMA50 > SMA200 ? 1 : 0
    "atr14_ratio",  # ATR(14)/close
    "vol_z",        # volume / 24-mum ort - 1
]

RSI_PERIOD = 14
SMA_FAST = 50
SMA_SLOW = 200
ATR_PERIOD = 14
VOL_WINDOW = 24
WARMUP_ROWS = SMA_SLOW - 1  # 199: en uzun pencere belirler


def _wilder_rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _wilder_atr(high: pd.Series, low: pd.Series, close: pd.Series,
                period: int = ATR_PERIOD) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([high - low,
                    (high - prev_close).abs(),
                    (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCV -> feature çerçevesi. Girdi sırası korunur, index korunur.

    Gerekli kolonlar: open, high, low, close, volume.
    Tüm pencereler geriye dönüktür (nedensel); satır i yalnızca <=i verisini görür.
    """
    need = {"open", "high", "low", "close", "volume"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"eksik kolonlar: {sorted(missing)}")
    close = df["close"].astype(float)
    out = pd.DataFrame(index=df.index)
    out["ret_1"] = close.pct_change(1)
    out["ret_12"] = close.pct_change(12)
    out["rsi14"] = _wilder_rsi(close)
    sma50 = close.rolling(SMA_FAST, min_periods=SMA_FAST).mean()
    sma200 = close.rolling(SMA_SLOW, min_periods=SMA_SLOW).mean()
    out["sma50_ratio"] = close / sma50 - 1
    out["sma200_ratio"] = close / sma200 - 1
    out["sma_trend"] = (sma50 > sma200).astype(float)
    out.loc[sma50.isna() | sma200.isna(), "sma_trend"] = np.nan
    out["atr14_ratio"] = _wilder_atr(df["high"].astype(float),
                                     df["low"].astype(float), close) / close
    out["vol_z"] = (df["volume"].astype(float)
                    / df["volume"].astype(float).rolling(VOL_WINDOW,
                                                         min_periods=VOL_WINDOW).mean()
                    - 1)
    return out[FEATURES]
