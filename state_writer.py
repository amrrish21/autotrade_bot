"""
state_writer.py — Writes bot state to bot_state.json every scan cycle.
Import this into bot.py to power the live dashboard.
"""

import json
import os
from datetime import datetime
from typing import TYPE_CHECKING

STATE_FILE = os.path.join(os.path.dirname(__file__), "bot_state.json")
import config


def write_state(order_mgr, risk_mgr, tracker, last_signals: dict = None, pnl_history: list = None):
    """
    Serialize the current bot state to bot_state.json.
    Called at the end of every scan loop in bot.py.
    """
    positions_data = {}
    for sym, pos in order_mgr.positions.items():
        positions_data[sym] = {
            "symbol":       pos.symbol,
            "instrument":   pos.instrument,
            "direction":    pos.direction,
            "qty":          pos.qty,
            "entry_price":  pos.entry_price,
            "stop_loss":    pos.stop_loss,
            "take_profit":  pos.take_profit,
            "entry_time":   pos.entry_time.isoformat(),
            "ltp":          pos.entry_price,   # will be updated by bot with real LTP
        }

    cap = config.MAX_CAPITAL
    pnl = order_mgr.daily_pnl

    wins   = [t for t in order_mgr.trade_log if t["pnl"] > 0]
    losses = [t for t in order_mgr.trade_log if t["pnl"] <= 0]
    win_rate = round(len(wins) / len(order_mgr.trade_log) * 100, 1) if order_mgr.trade_log else 0

    # Approximate capital deployed (sum of position values)
    capital_deployed = sum(
        pos.entry_price * pos.qty for pos in order_mgr.positions.values()
    )

    # Build signals dict
    signals_data = {}
    if last_signals:
        for sym, sig in last_signals.items():
            signals_data[sym] = {
                "signal":  sig.signal,
                "price":   sig.price,
                "reason":  sig.reason,
                "rsi":     sig.rsi,
            }

    state = {
        "timestamp":               datetime.now().isoformat(),
        "session_start":           tracker.start_time.isoformat(),
        "paper_trading":           config.PAPER_TRADING,
        "max_capital":             cap,
        "daily_pnl":               round(pnl, 2),
        "pnl_pct":                 round(pnl / cap * 100, 2),
        "total_trades":            order_mgr.total_trades,
        "win_rate":                win_rate,
        "trading_halted":          risk_mgr.trading_halted,
        "halt_reason":             risk_mgr.halt_reason,
        "capital_deployed":        round(capital_deployed, 2),
        "daily_profit_target_pct": config.DAILY_PROFIT_TARGET,
        "daily_loss_limit_pct":    config.DAILY_LOSS_LIMIT,
        "strategy":                f"EMA({config.EMA_SHORT}/{config.EMA_LONG})+RSI+MACD",
        "interval":                config.CANDLE_INTERVAL,
        "watchlist":               list(config.WATCHLIST.keys()),
        "positions":               positions_data,
        "trade_log":               order_mgr.trade_log[-50:],   # last 50 trades
        "last_signals":            signals_data,
        "pnl_history":             (pnl_history or [])[-120:],  # last 120 data points
        "indices": {
            "nifty50":   {"value": "24,832.65", "change": "+187.30 (+0.76%)"},
            "sensex":    {"value": "81,547.90", "change": "+542.80 (+0.67%)"},
            "banknifty": {"value": "51,234.10", "change": "-120.40 (-0.23%)"},
            "niftyit":   {"value": "38,742.55", "change": "+310.20 (+0.81%)"},
        },
    }

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
