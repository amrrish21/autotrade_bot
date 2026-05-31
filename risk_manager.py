"""
risk_manager.py — Daily loss limit, profit target, and trade guards.
"""

from datetime import datetime
import config
from logger import log
from notifier import send_notification


class RiskManager:
    def __init__(self):
        self.daily_pnl:       float = 0.0
        self.trading_halted:  bool  = False
        self.halt_reason:     str   = ""
        self.trades_today:    int   = 0
        self.start_capital:   float = config.MAX_CAPITAL

    def update_pnl(self, pnl_change: float):
        """Called every time a position closes."""
        self.daily_pnl += pnl_change
        self.trades_today += 1
        self._check_limits()

    def can_trade(self) -> tuple[bool, str]:
        """
        Returns (True, "") if trading is allowed.
        Returns (False, reason) if trading should be blocked.
        """
        if self.trading_halted:
            return False, self.halt_reason

        if not self._is_market_hours():
            return False, "Outside market hours (9:15 AM – 3:15 PM IST)"

        if self._is_squareoff_time():
            return False, "Square-off time (3:20 PM) — new trades blocked"

        return True, ""

    def should_squareoff(self) -> bool:
        """Returns True when it's time to close all intraday positions."""
        return self._is_squareoff_time()

    def status_line(self) -> str:
        pnl_pct = (self.daily_pnl / self.start_capital) * 100
        return (
            f"Daily P&L: ₹{self.daily_pnl:+.2f} ({pnl_pct:+.2f}%) | "
            f"Trades: {self.trades_today} | "
            f"{'🚫 HALTED' if self.trading_halted else '✅ ACTIVE'}"
        )

    # ── Private ────────────────────────────────────────────────────────────────

    def _check_limits(self):
        pnl_pct = (self.daily_pnl / self.start_capital) * 100

        if pnl_pct <= -config.DAILY_LOSS_LIMIT:
            self._halt(
                f"Daily loss limit hit ({pnl_pct:.2f}% ≤ -{config.DAILY_LOSS_LIMIT}%)"
            )

        elif pnl_pct >= config.DAILY_PROFIT_TARGET:
            self._halt(
                f"Daily profit target reached ({pnl_pct:.2f}% ≥ {config.DAILY_PROFIT_TARGET}%)"
            )

    def _halt(self, reason: str):
        if not self.trading_halted:
            self.trading_halted = True
            self.halt_reason    = reason
            log.warning(f"[risk] Trading halted: {reason}")
            send_notification(f"⛔ Bot halted: {reason}")

    @staticmethod
    def _is_market_hours() -> bool:
        now = datetime.now()
        oh, om = config.MARKET_OPEN
        ch, cm = config.MARKET_CLOSE
        open_time  = now.replace(hour=oh, minute=om, second=0, microsecond=0)
        close_time = now.replace(hour=ch, minute=cm, second=0, microsecond=0)
        return open_time <= now <= close_time

    @staticmethod
    def _is_squareoff_time() -> bool:
        now = datetime.now()
        sh, sm = config.SQUAREOFF_TIME
        squareoff = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
        return now >= squareoff
