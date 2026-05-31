"""
indicators.py — Technical indicator calculations (pure pandas/numpy, no TA-Lib needed).
"""

import pandas as pd
import numpy as np


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (Wilder's smoothing method).
    Returns values 0–100.
    """
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series,
         fast: int = 12, slow: int = 26, signal: int = 9
         ) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD indicator.
    Returns (macd_line, signal_line, histogram).
    """
    ema_fast   = ema(series, fast)
    ema_slow   = ema(series, slow)
    macd_line  = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram   = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(series: pd.Series,
                    period: int = 20, std_dev: float = 2.0
                    ) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands.
    Returns (upper_band, middle_band, lower_band).
    """
    middle = sma(series, period)
    std    = series.rolling(window=period).std()
    upper  = middle + std_dev * std
    lower  = middle - std_dev * std
    return upper, middle, lower


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range — measures volatility."""
    high  = df["high"]
    low   = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    return tr.ewm(alpha=1/period, adjust=False).mean()


def vwap(df: pd.DataFrame) -> pd.Series:
    """
    Volume Weighted Average Price — intraday only (resets each day).
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cum_tp_vol    = (typical_price * df["volume"]).cumsum()
    cum_vol       = df["volume"].cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


def add_all_indicators(df: pd.DataFrame,
                       ema_short: int = 9,
                       ema_long: int  = 21,
                       rsi_period: int = 14) -> pd.DataFrame:
    """
    Compute and attach all indicators to the DataFrame in one call.
    Returns the same DataFrame with new columns added.
    """
    close = df["close"]

    df["ema_short"]   = ema(close, ema_short)
    df["ema_long"]    = ema(close, ema_long)
    df["rsi"]         = rsi(close, rsi_period)
    df["vwap"]        = vwap(df)
    df["atr"]         = atr(df)

    df["macd"], df["macd_signal"], df["macd_hist"] = macd(close)

    df["bb_upper"], df["bb_mid"], df["bb_lower"] = bollinger_bands(close)

    # EMA crossover signal: +1 = bullish cross, -1 = bearish cross, 0 = no cross
    ema_diff = df["ema_short"] - df["ema_long"]
    df["ema_cross"] = np.sign(ema_diff).diff().fillna(0).astype(int)

    return df
