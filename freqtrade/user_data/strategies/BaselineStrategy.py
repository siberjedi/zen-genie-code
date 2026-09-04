"""
Faz 1 Baseline — Faz 2'de backtest referansı olacak.
Primary: OOS Sharpe. Faz 0 eşikleri kilitlenmeden değiştirilemez.
"""
from freqtrade.strategy import IStrategy, IntParameter
import talib.abstract as ta
import pandas as pd

class BaselineStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False
    use_exit_signal = True
    startup_candle_count = 200
    stoploss = -0.10
    minimal_roi = {"0": 0.02}

    buy_rsi = IntParameter(10, 40, default=30, space="buy")
    sell_rsi = IntParameter(60, 90, default=70, space="sell")

    def populate_indicators(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        df["rsi"] = ta.RSI(df, timeperiod=14)
        df["sma50"] = ta.SMA(df, timeperiod=50)
        df["sma200"] = ta.SMA(df, timeperiod=200)
        return df

    def populate_entry_trend(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        df.loc[
            (df["rsi"] < self.buy_rsi.value) & (df["sma50"] > df["sma200"]),
            "enter_long"] = 1
        return df

    def populate_exit_trend(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        df.loc[(df["rsi"] > self.sell_rsi.value), "exit_long"] = 1
        return df
