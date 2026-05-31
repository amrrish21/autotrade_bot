"""
strategy.py — Trading signal generation.

Signal logic (EMA crossover + RSI filter + MACD confirmation):
  BUY  when:
    - EMA_SHORT crosses ABOVE EMA_LONG  (bullish crossover)
    - RSI is between 40 and RSI_OVERBOUGHT (not overbought)
    - MACD histogram > 0  (bullish momentum)
    - Price is above VWAP  (trend confirmation)

  SELL when:
    - EMA_SHORT crosses BELOW EMA_LONG  (bearish crossover)
    - RSI is between RSI_OVERSOLD and 60 (not oversold)
    - MACD histogram < 0  (bearish momentum)
    - Price is below VWAP  (trend confirmation)

  HOLD otherwise.
"""

import pandas as pd
from dataclasses import dataclass
from typing import Literal
import config
import indicators


Signal = Literal["BUY", "SELL", "HOLD"]


@dataclass
class TradeSignal:
    symbol:    str
    signal:    Signal
    price:     float
    stop_loss: float
    take_profit: float
    rsi:       float
    reason:    str


def generate_signal(symbol: str, df: pd.DataFrame) -> TradeSignal:
    """
    Run indicator logic on a candle DataFrame and return a TradeSignal.
    df must have at least 50 rows (enough for all indicators to warm up).
    """
    if len(df) < 50:
        return _hold(symbol, df["close"].iloc[-1], "Not enough candle data")

    # Compute all indicators
    df = indicators.add_all_indicators(
        df.copy(),
        ema_short  = config.EMA_SHORT,
        ema_long   = config.EMA_LONG,
        rsi_period = config.RSI_PERIOD,
    )

    # Last two rows for crossover detection
    last  = df.iloc[-1]
    prev  = df.iloc[-2]

    price       = float(last["close"])
    rsi_val     = float(last["rsi"])
    macd_hist   = float(last["macd_hist"])
    ema_short   = float(last["ema_short"])
    ema_long    = float(last["ema_long"])
    vwap_val    = float(last["vwap"])
    cross       = float(last["ema_cross"])

    # ── BUY conditions ──────────────────────────────────────────────────────
    buy_cross   = (cross == 2)                                   # +1 → +1 diff = 2 means fresh bullish cross
    buy_cross   = (float(prev["ema_short"]) < float(prev["ema_long"])) and (ema_short > ema_long)
    rsi_ok_buy  = config.RSI_OVERSOLD < rsi_val < config.RSI_OVERBOUGHT
    macd_bull   = macd_hist > 0
    above_vwap  = price > vwap_val

    if buy_cross and rsi_ok_buy and macd_bull and above_vwap:
        sl = round(price * (1 - config.STOP_LOSS_PCT   / 100), 2)
        tp = round(price * (1 + config.TAKE_PROFIT_PCT / 100), 2)
        reason = (
            f"EMA{config.EMA_SHORT} crossed above EMA{config.EMA_LONG} | "
            f"RSI={rsi_val:.1f} | MACD hist={macd_hist:.2f} | "
            f"Price {price:.2f} > VWAP {vwap_val:.2f}"
        )
        return TradeSignal(symbol, "BUY", price, sl, tp, rsi_val, reason)

    # ── SELL conditions ─────────────────────────────────────────────────────
    sell_cross   = (float(prev["ema_short"]) > float(prev["ema_long"])) and (ema_short < ema_long)
    rsi_ok_sell  = config.RSI_OVERSOLD < rsi_val < (config.RSI_OVERBOUGHT - 10)
    macd_bear    = macd_hist < 0
    below_vwap   = price < vwap_val

    if sell_cross and rsi_ok_sell and macd_bear and below_vwap:
        sl = round(price * (1 + config.STOP_LOSS_PCT   / 100), 2)
        tp = round(price * (1 - config.TAKE_PROFIT_PCT / 100), 2)
        reason = (
            f"EMA{config.EMA_SHORT} crossed below EMA{config.EMA_LONG} | "
            f"RSI={rsi_val:.1f} | MACD hist={macd_hist:.2f} | "
            f"Price {price:.2f} < VWAP {vwap_val:.2f}"
        )
        return TradeSignal(symbol, "SELL", price, sl, tp, rsi_val, reason)

    # ── HOLD ────────────────────────────────────────────────────────────────
    return _hold(symbol, price,
                 f"No crossover | RSI={rsi_val:.1f} | MACD hist={macd_hist:.2f}")


def _hold(symbol: str, price: float, reason: str) -> TradeSignal:
    return TradeSignal(
        symbol      = symbol,
        signal      = "HOLD",
        price       = price,
        stop_loss   = 0.0,
        take_profit = 0.0,
        rsi         = 0.0,
        reason      = reason,
    )
