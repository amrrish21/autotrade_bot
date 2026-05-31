"""
order_manager.py — Place, track, and close orders via Upstox API.

In PAPER_TRADING mode (default) all orders are simulated locally — nothing
is sent to the exchange. Set PAPER_TRADING=false in .env for live trading.
"""

import requests
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
import config
from logger import log
from notifier import send_notification

BASE_URL = "https://api.upstox.com/v2"


@dataclass
class Position:
    symbol:       str
    instrument:   str
    direction:    str          # BUY or SELL
    qty:          int
    entry_price:  float
    stop_loss:    float
    take_profit:  float
    entry_time:   datetime     = field(default_factory=datetime.now)
    order_id:     str          = ""
    pnl:          float        = 0.0


class OrderManager:
    def __init__(self):
        self.positions: dict[str, Position] = {}   # symbol → Position
        self.trade_log: list[dict]           = []
        self.daily_pnl: float                = 0.0
        self.total_trades: int               = 0

    # ── Public API ─────────────────────────────────────────────────────────────

    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions

    def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)

    def open_position(self, symbol: str, instrument: str,
                      direction: str, price: float,
                      stop_loss: float, take_profit: float) -> bool:
        """
        Calculate position size, then buy/sell.
        Returns True if the order was placed successfully.
        """
        if self.has_position(symbol):
            log.warning(f"[order] Already have a position in {symbol}, skipping")
            return False

        qty = self._calculate_qty(price)
        if qty <= 0:
            log.warning(f"[order] Quantity is 0 for {symbol} at ₹{price:.2f}, skipping")
            return False

        if config.PAPER_TRADING:
            order_id = f"PAPER-{uuid.uuid4().hex[:8].upper()}"
            log.info(f"[PAPER] {direction} {qty} x {symbol} @ ₹{price:.2f} | "
                     f"SL=₹{stop_loss:.2f} TP=₹{take_profit:.2f} | order_id={order_id}")
        else:
            order_id = self._place_upstox_order(instrument, direction, qty, price)
            if not order_id:
                return False

        pos = Position(
            symbol      = symbol,
            instrument  = instrument,
            direction   = direction,
            qty         = qty,
            entry_price = price,
            stop_loss   = stop_loss,
            take_profit = take_profit,
            order_id    = order_id,
        )
        self.positions[symbol] = pos
        self.total_trades += 1

        msg = (f"{'📄 PAPER' if config.PAPER_TRADING else '✅ LIVE'} "
               f"{direction} {qty}×{symbol} @ ₹{price:.2f} | "
               f"SL ₹{stop_loss:.2f} | TP ₹{take_profit:.2f}")
        send_notification(msg)
        return True

    def close_position(self, symbol: str, exit_price: float, reason: str) -> float:
        """
        Close an open position. Returns realised P&L.
        """
        pos = self.positions.get(symbol)
        if not pos:
            return 0.0

        if pos.direction == "BUY":
            pnl = (exit_price - pos.entry_price) * pos.qty
        else:
            pnl = (pos.entry_price - exit_price) * pos.qty

        self.daily_pnl += pnl
        pos.pnl = pnl

        if config.PAPER_TRADING:
            log.info(f"[PAPER] CLOSE {symbol} @ ₹{exit_price:.2f} | "
                     f"P&L = ₹{pnl:+.2f} | Reason: {reason}")
        else:
            self._place_upstox_order(
                pos.instrument,
                "SELL" if pos.direction == "BUY" else "BUY",
                pos.qty,
                exit_price,
            )

        self.trade_log.append({
            "symbol":      symbol,
            "direction":   pos.direction,
            "qty":         pos.qty,
            "entry":       pos.entry_price,
            "exit":        exit_price,
            "pnl":         round(pnl, 2),
            "reason":      reason,
            "time":        datetime.now().isoformat(),
        })

        del self.positions[symbol]

        emoji = "🟢" if pnl >= 0 else "🔴"
        msg = (f"{emoji} CLOSED {symbol} @ ₹{exit_price:.2f} | "
               f"P&L ₹{pnl:+.2f} | {reason}")
        send_notification(msg)
        return pnl

    def check_sl_tp(self, symbol: str, ltp: float):
        """Call on every price tick to auto-trigger stop-loss or take-profit."""
        pos = self.positions.get(symbol)
        if not pos:
            return

        if pos.direction == "BUY":
            if ltp <= pos.stop_loss:
                self.close_position(symbol, ltp, "Stop-loss triggered")
            elif ltp >= pos.take_profit:
                self.close_position(symbol, ltp, "Take-profit hit")
        else:  # SELL / short
            if ltp >= pos.stop_loss:
                self.close_position(symbol, ltp, "Stop-loss triggered")
            elif ltp <= pos.take_profit:
                self.close_position(symbol, ltp, "Take-profit hit")

    def close_all_positions(self, ltp_map: dict, reason: str = "End-of-day square-off"):
        """Force-close every open position (called at 3:20 PM)."""
        for symbol in list(self.positions.keys()):
            price = ltp_map.get(self.positions[symbol].instrument, 0)
            if price > 0:
                self.close_position(symbol, price, reason)
            else:
                log.warning(f"[order] Could not get LTP for {symbol}, skipping close")

    def daily_summary(self) -> str:
        wins   = [t for t in self.trade_log if t["pnl"] > 0]
        losses = [t for t in self.trade_log if t["pnl"] <= 0]
        return (
            f"\n{'='*50}\n"
            f"  📊 Daily Summary\n"
            f"{'='*50}\n"
            f"  Total trades : {self.total_trades}\n"
            f"  Winners      : {len(wins)}\n"
            f"  Losers       : {len(losses)}\n"
            f"  Net P&L      : ₹{self.daily_pnl:+.2f}\n"
            f"  Win rate     : "
            f"{len(wins)/self.total_trades*100:.1f}%\n"
            f"{'='*50}\n"
        ) if self.total_trades else "No trades today."

    # ── Private helpers ────────────────────────────────────────────────────────

    def _calculate_qty(self, price: float) -> int:
        """Risk-based position sizing: never risk more than RISK_PER_TRADE_PCT of capital."""
        risk_amount   = config.MAX_CAPITAL * (config.RISK_PER_TRADE_PCT / 100)
        risk_per_unit = price * (config.STOP_LOSS_PCT / 100)
        if risk_per_unit <= 0:
            return 0
        qty = int(risk_amount / risk_per_unit)
        # Also cap so total position value ≤ 20% of capital
        max_by_capital = int((config.MAX_CAPITAL * 0.20) / price)
        return min(qty, max_by_capital)

    def _place_upstox_order(self, instrument: str, transaction_type: str,
                             qty: int, price: float) -> Optional[str]:
        """Send a real order to Upstox. Returns order_id or None on failure."""
        url = f"{BASE_URL}/order/place"
        headers = {
            "Authorization": f"Bearer {config.ACCESS_TOKEN}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }
        payload = {
            "quantity":           qty,
            "product":            "I",           # I = intraday (MIS)
            "validity":           "DAY",
            "price":              0,              # 0 = MARKET order
            "tag":                "upstox_bot",
            "instrument_token":   instrument,
            "order_type":         "MARKET",
            "transaction_type":   transaction_type,
            "disclosed_quantity": 0,
            "trigger_price":      0,
            "is_amo":             False,
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            order_id = data.get("data", {}).get("order_id", "")
            log.info(f"[order] Upstox order placed: {order_id}")
            return order_id
        except requests.HTTPError as e:
            log.error(f"[order] HTTP error placing order: {e.response.text}")
        except Exception as e:
            log.error(f"[order] Error placing order: {e}")
        return None
