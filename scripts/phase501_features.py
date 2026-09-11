"""Phase 5 — Feature union (28) + frozen blocks B0/B1/B2/B3 (kilitli, DESIGN 500).

Tüm pencereler geriye dönüktür (nedensel): feature[t] yalnızca mum <= t bilgisi
görür. Yasak: ileri-bakan shift, centered rolling, ileriye dönük fill.
(DESIGN sec 7/8)
Sıfır-range mumlar (range=0) ilgili candle-structure feature'larında NaN bırakir.
15m resample: tamamlanmış bar (open=first, high=max, low=min, close=last,
volume=sum); eksik/kısmi son bar DÜŞER (DESIGN sec 4).
"""
import numpy as np
import pandas as pd

FEATURE_UNION = [
    # A) Returns
    "ret_1", "ret_3", "ret_12", "ret_36", "ret_72",
    # B) Trend
    "sma50_ratio", "sma200_ratio", "ema12_ratio", "ema26_ratio",
    "sma_trend", "sma50_slope",
    # C) Momentum
    "rsi14", "roc_36", "ema_diff_12_26",
    # D) Volatility
    "atr14_ratio", "roll_std_24_ratio", "rv_12", "vol_percentile_1d",
    # E) Volume
    "vol_z", "vol_change", "vol_ratio_168",
    # F) Candle structure
    "body_ratio", "up_wick_ratio", "low_wick_ratio", "close_pos", "range_pct",
    # G) Regime
    "adx14_ratio", "vol_rank_288",
]

BLOCKS = {
    "B0": ["ret_1", "ret_3", "ret_12", "ret_36", "ret_72",
           "sma50_ratio", "sma200_ratio", "ema12_ratio", "ema26_ratio",
           "sma_trend", "sma50_slope",
           "vol_z", "vol_change", "vol_ratio_168"],
    "B1": ["rsi14", "roc_36", "ema_diff_12_26",
           "atr14_ratio", "roll_std_24_ratio", "rv_12", "vol_percentile_1d"],
    "B2": ["body_ratio", "up_wick_ratio", "low_wick_ratio", "close_pos",
           "range_pct", "adx14_ratio", "vol_rank_288"],
    "B3": FEATURE_UNION,
}

RSI_PERIOD = 14
ATR_PERIOD = 14
ADX_PERIOD = 14
SMA_FAST = 50
SMA_SLOW = 200
EMA_FAST = 12
EMA_SLOW = 26
RV_WINDOW = 12
VOL_WINDOW = 24
VOL_WEEK = 168
PCT_WINDOW_1D = 288
PCT_WINDOW_ATR = 288
ROLL_STD_WINDOW = 24
RET_PCT_K = [1, 3, 12, 36, 72]


def _wilder_rsi(close, period=RSI_PERIOD):
    """Wilder RSI(14) — src/freqai/features.py ile aynı matematik."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _wilder_atr(high, low, close, period=ATR_PERIOD):
    """Wilder ATR(14) — src/freqai/features.py ile aynı matematik."""
    prev_close = close.shift(1)
    tr = pd.concat([high - low,
                    (high - prev_close).abs(),
                    (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def _wilder_rma(x, period):
    """Wilder yumuşatma (RMA) — TA-Lib ile aynı: ilk `period` değerinin basit
    ortalaması seed alır, sonra (x_i + (period-1)*prev)/period."""

    def _rma_loop(values):
        n = len(values)
        out = np.full(n, np.nan)
        if n < period:
            return out
        if np.isnan(values[:period]).any():
            return out
        prev = values[:period].mean()
        out[period - 1] = prev
        for i in range(period, n):
            if np.isnan(values[i]):
                out[i] = np.nan
                break
            prev = (values[i] + (period - 1) * prev) / period
            out[i] = prev
        return out

    return pd.Series(_rma_loop(x.to_numpy()), index=x.index)


def _rma_from_first_valid(x, period):
    """RMA ilk GECERLI degerden baslar (NaN öneki kirpilir) — ADX DX zinciri icin.

    src/freqai + talib: ADX lookback = 2*period - 1; DX serisi pdi/mdi'den sonra
    geldigi icin basinda NaN bulunur. RMA yalnizca gecerli segment üzerinde kosar.
    """
    vals = x.to_numpy()
    k = 0
    while k < len(vals) and np.isnan(vals[k]):
        k += 1
    if len(vals) - k < period:
        return pd.Series(np.full(len(vals), np.nan), index=x.index)
    out = np.full(len(vals), np.nan)
    seg = vals[k:]
    prev = seg[:period].mean()
    out[k + period - 1] = prev
    for i in range(1, len(seg) - period + 1):
        prev = (seg[period - 1 + i] + (period - 1) * prev) / period
        out[k + period - 1 + i] = prev
    return pd.Series(out, index=x.index)


def _wilder_adx(high, low, close, period=ADX_PERIOD):
    """Wilder ADX(14)/100 — talib.abstract.ADX/100 ile aynı mekanik matematik.

    2026-09-07 not: host'ta talib yok; lock'lu rejim sınıflandırıcısıyla birebir
    aynı formül (TR, +DM/-DM Wilder yumuşatma, DX, ADX = DX'in Wilder RMA'sı).
    """
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
                        index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
                         index=high.index)
    tr = pd.concat([high - low,
                    (high - prev_close).abs(),
                    (low - prev_close).abs()], axis=1).max(axis=1)
    tr_s = _wilder_rma(tr, period)
    pdm_s = _wilder_rma(plus_dm, period)
    mdm_s = _wilder_rma(minus_dm, period)
    pdi = 100 * pdm_s / tr_s
    mdi = 100 * mdm_s / tr_s
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    adx = _rma_from_first_valid(dx, period)
    return adx / 100.0


def _roll_pct_rank_lowest(x, window):
    """Nedensel (trailing) pencere içinde son değerin yüzde sırası [0,1]."""
    return x.rolling(window, min_periods=window).apply(
        lambda w: float((w <= w[-1]).mean()), raw=True)


def build_features(df):
    """OHLCV -> 28 feature. Girdi sırası korunur, index korunur.

    feature[t] yalnızca mum <= t bilgisini kullanır (katalog geriye dönük).
    range=0 mumlarda candle-structure NaN (doldurma yok, düşürme var).
    """
    need = {"open", "high", "low", "close", "volume"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"eksik kolonlar: {sorted(missing)}")
    open_ = df["open"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    out = pd.DataFrame(index=df.index)

    for k in RET_PCT_K:
        out[f"ret_{k}"] = close.pct_change(k)
    sma50 = close.rolling(SMA_FAST, min_periods=SMA_FAST).mean()
    sma200 = close.rolling(SMA_SLOW, min_periods=SMA_SLOW).mean()
    out["sma50_ratio"] = close / sma50 - 1
    out["sma200_ratio"] = close / sma200 - 1
    ema12 = close.ewm(span=EMA_FAST, adjust=False).mean()
    ema26 = close.ewm(span=EMA_SLOW, adjust=False).mean()
    out["ema12_ratio"] = close / ema12 - 1
    out["ema26_ratio"] = close / ema26 - 1
    out["sma_trend"] = (sma50 > sma200).astype(float)
    out.loc[sma50.isna() | sma200.isna(), "sma_trend"] = np.nan
    out["sma50_slope"] = sma50 / sma50.shift(12) - 1

    out["rsi14"] = _wilder_rsi(close)
    out["roc_36"] = close.pct_change(36)
    out["ema_diff_12_26"] = (ema12 - ema26) / close

    rsi14_loc = out["rsi14"]
    atr14 = _wilder_atr(high, low, close)
    out["atr14_ratio"] = atr14 / close
    out["roll_std_24_ratio"] = close.rolling(ROLL_STD_WINDOW, min_periods=ROLL_STD_WINDOW).std() / close
    out["rv_12"] = close.pct_change(1).rolling(RV_WINDOW, min_periods=RV_WINDOW).std() * np.sqrt(288 * 365)
    out["vol_percentile_1d"] = _roll_pct_rank_lowest(
        close.rolling(ROLL_STD_WINDOW, min_periods=ROLL_STD_WINDOW).std(), PCT_WINDOW_1D)

    out["vol_z"] = volume / volume.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).mean() - 1
    out["vol_change"] = volume.pct_change(1)
    out["vol_ratio_168"] = volume / volume.rolling(VOL_WEEK, min_periods=VOL_WEEK).mean() - 1

    rng = high - low
    out["body_ratio"] = (close - open_).abs() / rng
    out["up_wick_ratio"] = (high - pd.concat([open_, close], axis=1).max(axis=1)) / rng
    out["low_wick_ratio"] = (pd.concat([open_, close], axis=1).min(axis=1) - low) / rng
    out["close_pos"] = (close - low) / rng
    out["range_pct"] = rng / close
    out.loc[rng == 0, ["body_ratio", "up_wick_ratio", "low_wick_ratio",
                       "close_pos", "range_pct"]] = np.nan

    out["adx14_ratio"] = _wilder_adx(high, low, close)
    out["vol_rank_288"] = _roll_pct_rank_lowest(atr14, PCT_WINDOW_ATR)

    # Sifir-vol mumlar (erken dönem) vol_z/vol_change/vol_ratio_168 ve sma50_slope
    # icin +/-inf uretir; dropna inf yakalamaz. NaN politikasi: doldurma yok,
    # dusurme var -> inf -> NaN (katalog disi, kilitli politika, degisiklik yok).
    out.replace([np.inf, -np.inf], np.nan, inplace=True)

    return out[FEATURE_UNION]


def causality_probe(df_cols_forbids=(".shift(-", "ewm(center=")):
    """Bu modülün kaynak kodunda ileriye bakan op olmadığını kabaca doğrular."""
    import inspect
    src = inspect.getsource(build_features) + inspect.getsource(resample_15m)
    for bad in df_cols_forbids:
        assert bad not in src, f"yasaki operator tespit edildi: {bad}"


def resample_15m(df5):
    """5m -> 15m tamamlanmış bar resample (nedensel). Kısmi son bar düşer.

    Tamamlanmış bar: bir 15m aralığında 3 adet 5m mum (0/5/10 dk dilimleri)
    mevcut olmalı. open=first, high=max, low=min, close=last, volume=sum.
    """
    need = {"date", "open", "high", "low", "close", "volume"}
    missing = need - set(df5.columns)
    if missing:
        raise ValueError(f"eksik kolonlar: {sorted(missing)}")
    df = df5.copy()
    df["_t"] = pd.to_datetime(df["date"])
    if getattr(df["_t"].dt, "tz", None) is None:
        df["_t"] = df["_t"].dt.tz_localize("UTC")
    df = df.sort_values("_t").reset_index(drop=True)
    df["_bucket"] = df["_t"].dt.floor("15min")
    df["_minute"] = df["_t"].dt.minute % 15
    complete = df.groupby("_bucket")["_minute"].apply(
        lambda s: set(s.tolist()) == {0, 5, 10})
    comp_buckets = set(complete.index[complete.values.astype(bool)])
    df = df[df["_bucket"].isin(comp_buckets)]
    agg = (df.groupby("_bucket")
             .agg(open=("open", "first"), high=("high", "max"),
                  low=("low", "min"), close=("close", "last"),
                  volume=("volume", "sum"))
             .reset_index())
    agg["date"] = pd.to_datetime(agg["_bucket"])
    if getattr(agg["date"].dt, "tz", None) is None:
        agg["date"] = agg["date"].dt.tz_localize("UTC")
    out = agg[["date", "open", "high", "low", "close", "volume"]].reset_index(drop=True)
    return out


def block_features(block):
    if block not in BLOCKS:
        raise KeyError(f"bilinmeyen blok: {block}")
    return BLOCKS[block]


def diaspora_check(df, feats):
    """feature NaN politikası: doldurma yok, düşürme var."""
    return df[feats]


if __name__ == "__main__":
    import pathlib
    import sys
    ROOT = pathlib.Path(__file__).parents[1]
    sys.path.insert(0, str(ROOT))
    src = pd.read_feather("freqtrade/user_data/data/binance/BTC_USDT-5m.feather")
    src = src[(src["date"] >= "2020-01-01") & (src["date"] <= "2023-06-30 23:55")]
    f5 = build_features(src)
    f15 = build_features(resample_15m(src))
    print(f"5m features: {f5.shape} nan={f5.isna().sum().sum()}")
    print(f"15m features: {f15.shape} nan={f15.isna().sum().sum()}")
    for b, cols in BLOCKS.items():
        print(f"{b}: {len(cols)} feature")