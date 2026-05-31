"""
portfolio_tracker.py — Tracks trade history, P&L stats, and saves a daily report.
"""

import json
import os
import csv
from datetime import datetime
from typing import List
from logger import log

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


class PortfolioTracker:
    def __init__(self):
        self.trades:     List[dict] = []
        self.start_time: datetime   = datetime.now()

    def record_trade(self, symbol: str, direction: str, qty: int,
                     entry: float, exit_price: float, pnl: float,
                     reason: str):
        self.trades.append({
            "timestamp": datetime.now().isoformat(),
            "symbol":    symbol,
            "direction": direction,
            "qty":       qty,
            "entry":     round(entry, 2),
            "exit":      round(exit_price, 2),
            "pnl":       round(pnl, 2),
            "reason":    reason,
        })

    def stats(self) -> dict:
        if not self.trades:
            return {"total": 0}
        wins   = [t for t in self.trades if t["pnl"] > 0]
        losses = [t for t in self.trades if t["pnl"] <= 0]
        total_pnl = sum(t["pnl"] for t in self.trades)
        return {
            "total":     len(self.trades),
            "wins":      len(wins),
            "losses":    len(losses),
            "win_rate":  round(len(wins) / len(self.trades) * 100, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_win":   round(sum(t["pnl"] for t in wins)   / len(wins),   2) if wins   else 0,
            "avg_loss":  round(sum(t["pnl"] for t in losses) / len(losses), 2) if losses else 0,
        }

    def print_summary(self):
        s = self.stats()
        if s["total"] == 0:
            log.info("[portfolio] No trades recorded today.")
            return
        log.info("\n" + "="*55)
        log.info("  DAILY REPORT")
        log.info("="*55)
        log.info(f"  Total trades  : {s['total']}")
        log.info(f"  Winners       : {s['wins']}  |  Losers: {s['losses']}")
        log.info(f"  Win rate      : {s['win_rate']}%")
        log.info(f"  Net P&L       : ₹{s['total_pnl']:+.2f}")
        log.info(f"  Avg win       : ₹{s['avg_win']:+.2f}")
        log.info(f"  Avg loss      : ₹{s['avg_loss']:+.2f}")
        log.info("="*55)

    def save_report(self):
        """Save trade log as JSON and CSV."""
        date_str = datetime.now().strftime("%Y%m%d")

        json_path = os.path.join(REPORTS_DIR, f"trades_{date_str}.json")
        with open(json_path, "w") as f:
            json.dump({"stats": self.stats(), "trades": self.trades}, f, indent=2)

        csv_path = os.path.join(REPORTS_DIR, f"trades_{date_str}.csv")
        if self.trades:
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.trades[0].keys())
                writer.writeheader()
                writer.writerows(self.trades)

        log.info(f"[portfolio] Report saved → {json_path}")
        log.info(f"[portfolio] CSV saved    → {csv_path}")
