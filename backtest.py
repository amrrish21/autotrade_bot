"""
backtest.py — Offline strategy backtester using historical candle data.

Usage:
    python backtest.py                    # backtests all watchlist symbols
    python backtest.py RELIANCE TCS INFY  # backtests specific symbols

This runs entirely offline using the Upstox historical candle API.
No orders are placed. Use this to tune your strategy before going live.
"""

import sys
import pandas as pd
from datetime import datetime

import config
from market_data import get_candles
from strategy import generate_signal
from indicators import add_all_indicators
from logger import log


def backtest_symbol(symbol: str, instrument: str,
                    initial_capital: float = 100000,
                    days: int = 90) -> dict:
    """
    Walk-forward backtest: simulate the strategy on historical data.
    Returns a stats dict.
    """
    log.info(f"[backtest] Fetching {days} days of data for {symbol}...")
    df = get_candles(instrument, config.CANDLE_INTERVAL, days=days)
    if df is None or len(df) < 60:
        log.warning(f"[backtest] Not enough data for {symbol}")
        return {}

    df = add_all_indicators(df,
                            ema_short  = config.EMA_SHORT,
                            ema_long   = config.EMA_LONG,
                            rsi_period = config.RSI_PERIOD)

    capital    = initial_capital
    trades     = []
    position   = None   # dict with entry info when in a trade

    for i in range(50, len(df)):
        row      = df.iloc[i]
        prev_row = df.iloc[i - 1]
        price    = float(row["close"])
        rsi_val  = float(row["rsi"])
        macd_h   = float(row["macd_hist"])
        vwap_v   = float(row["vwap"])
        ema_s    = float(row["ema_short"])
        ema_l    = float(row["ema_long"])
        prev_s   = float(prev_row["ema_short"])
        prev_l   = float(prev_row["ema_long"])

        # Check SL / TP on open position
        if position:
            hit_sl = price <= position["sl"]
            hit_tp = price >= position["tp"]
            if hit_sl or hit_tp:
                pnl = (price - position["entry"]) * position["qty"]
                capital += pnl
                trades.append({
                    "entry_time": position["entry_time"],
                    "exit_time":  str(row["timestamp"]),
                    "symbol":     symbol,
                    "entry":      position["entry"],
                    "exit":       price,
                    "qty":        position["qty"],
                    "pnl":        round(pnl, 2),
                    "reason":     "TP" if hit_tp else "SL",
                })
                position = None

        # Look for BUY signal (long only in backtest)
        if not position:
            bullish_cross = (prev_s < prev_l) and (ema_s > ema_l)
            rsi_ok        = config.RSI_OVERSOLD < rsi_val < config.RSI_OVERBOUGHT
            macd_bull     = macd_h > 0
            above_vwap    = price > vwap_v

            if bullish_cross and rsi_ok and macd_bull and above_vwap:
                sl  = price * (1 - config.STOP_LOSS_PCT   / 100)
                tp  = price * (1 + config.TAKE_PROFIT_PCT / 100)
                risk_amount = capital * (config.RISK_PER_TRADE_PCT / 100)
                risk_per_unit = price * (config.STOP_LOSS_PCT / 100)
                qty = max(1, int(risk_amount / risk_per_unit))
                position = {
                    "entry":      price,
                    "sl":         sl,
                    "tp":         tp,
                    "qty":        qty,
                    "entry_time": str(row["timestamp"]),
                }

    # Close any open position at end of data
    if position:
        price = float(df.iloc[-1]["close"])
        pnl   = (price - position["entry"]) * position["qty"]
        capital += pnl
        trades.append({
            "entry_time": position["entry_time"],
            "exit_time":  str(df.iloc[-1]["timestamp"]),
            "symbol":     symbol,
            "entry":      position["entry"],
            "exit":       price,
            "qty":        position["qty"],
            "pnl":        round(pnl, 2),
            "reason":     "End of data",
        })

    # Stats
    if not trades:
        return {"symbol": symbol, "trades": 0}

    wins      = [t for t in trades if t["pnl"] > 0]
    losses    = [t for t in trades if t["pnl"] <= 0]
    total_pnl = sum(t["pnl"] for t in trades)

    return {
        "symbol":      symbol,
        "trades":      len(trades),
        "wins":        len(wins),
        "losses":      len(losses),
        "win_rate":    round(len(wins) / len(trades) * 100, 1),
        "total_pnl":   round(total_pnl, 2),
        "return_pct":  round(total_pnl / initial_capital * 100, 2),
        "avg_win":     round(sum(t["pnl"] for t in wins)   / len(wins),   2) if wins   else 0,
        "avg_loss":    round(sum(t["pnl"] for t in losses) / len(losses), 2) if losses else 0,
        "profit_factor": round(
            abs(sum(t["pnl"] for t in wins)) / abs(sum(t["pnl"] for t in losses)), 2
        ) if losses and sum(t["pnl"] for t in losses) != 0 else float("inf"),
        "trade_log": trades,
    }


def print_results(results: list[dict]):
    print("\n" + "="*65)
    print("  BACKTEST RESULTS")
    print("="*65)
    print(f"  {'Symbol':<14} {'Trades':>6} {'Win%':>6} {'P&L':>10} {'Ret%':>7} {'PF':>6}")
    print("  " + "-"*60)
    for r in results:
        if not r or r.get("trades", 0) == 0:
            continue
        print(f"  {r['symbol']:<14} {r['trades']:>6} {r['win_rate']:>5.1f}% "
              f"₹{r['total_pnl']:>9,.2f} {r['return_pct']:>6.2f}% {r['profit_factor']:>6.2f}")
    print("="*65 + "\n")


if __name__ == "__main__":
    symbols_to_test = sys.argv[1:] if len(sys.argv) > 1 else list(config.WATCHLIST.keys())
    log.info(f"[backtest] Testing {len(symbols_to_test)} symbol(s): {', '.join(symbols_to_test)}")

    results = []
    for sym in symbols_to_test:
        instrument = config.WATCHLIST.get(sym)
        if not instrument:
            log.warning(f"[backtest] {sym} not in WATCHLIST — skipping")
            continue
        r = backtest_symbol(sym, instrument)
        results.append(r)
        if r and r.get("trades", 0) > 0:
            log.info(f"[backtest] {sym}: {r['trades']} trades | "
                     f"Win: {r['win_rate']}% | P&L: ₹{r['total_pnl']:+,.2f}")

    print_results(results)
