"""
bot.py — Main trading bot loop.

Run BOTH of these (in two separate terminals):
    Terminal 1:  python bot.py          ← does the actual trading
    Terminal 2:  python dashboard.py    ← serves the live web dashboard

Then open http://localhost:5000 in your browser.
"""

import time
import signal
import sys
from datetime import datetime

import config
from logger import log
from market_data import get_candles, get_ltp
from strategy import generate_signal, TradeSignal
from order_manager import OrderManager
from risk_manager import RiskManager
from portfolio_tracker import PortfolioTracker
from notifier import send_notification
from state_writer import write_state


# ── Graceful shutdown ──────────────────────────────────────────────────────────
_running = True

def _handle_sigint(sig, frame):
    global _running
    log.warning("\n[bot] Ctrl+C — finishing current scan then shutting down...")
    _running = False

signal.signal(signal.SIGINT, _handle_sigint)


# ── Validation ─────────────────────────────────────────────────────────────────
def _validate_config():
    missing = []
    if not config.API_KEY or config.API_KEY == "your_api_key_here":
        missing.append("UPSTOX_API_KEY")
    if not config.API_SECRET or config.API_SECRET == "your_api_secret_here":
        missing.append("UPSTOX_API_SECRET")
    if not config.ACCESS_TOKEN or config.ACCESS_TOKEN == "your_access_token_here":
        missing.append("UPSTOX_ACCESS_TOKEN")
    if missing:
        log.error("="*55)
        log.error("  Missing credentials in .env:")
        for m in missing:
            log.error(f"    • {m}")
        log.error("")
        log.error("  Fix: run  python auth.py  to generate your token")
        log.error("="*55)
        sys.exit(1)


# ── Wait for market open ───────────────────────────────────────────────────────
def _wait_for_market_open():
    while _running:
        now = datetime.now()
        if now.weekday() >= 5:
            log.info(f"[bot] Weekend — market closed. Sleeping 1h...")
            time.sleep(3600)
            continue
        oh, om = config.MARKET_OPEN
        open_dt = now.replace(hour=oh, minute=om, second=0, microsecond=0)
        if now >= open_dt:
            return
        wait_sec = (open_dt - now).total_seconds()
        log.info(f"[bot] Market opens at 09:15 — waiting {wait_sec/60:.1f} min...")
        while wait_sec > 0 and _running:
            time.sleep(min(30, wait_sec))
            wait_sec -= 30


# ── Fetch LTPs for open positions ──────────────────────────────────────────────
def _fetch_ltps(order_mgr: OrderManager) -> dict:
    if not order_mgr.positions:
        return {}
    tokens = [pos.instrument for pos in order_mgr.positions.values()]
    return get_ltp(tokens)


# ── One scan cycle ─────────────────────────────────────────────────────────────
def _run_scan(order_mgr: OrderManager,
              risk_mgr: RiskManager,
              tracker: PortfolioTracker,
              pnl_history: list,
              last_signals: dict) -> dict:
    """
    Returns updated last_signals dict.
    """
    # 1. Monitor open positions for SL / TP
    if order_mgr.positions:
        ltp_map = _fetch_ltps(order_mgr)
        # Patch LTP into state for dashboard display
        for sym, pos in order_mgr.positions.items():
            ltp = ltp_map.get(pos.instrument, pos.entry_price)
            pos.__dict__["ltp"] = ltp   # attach for state_writer

        for symbol, pos in list(order_mgr.positions.items()):
            ltp = ltp_map.get(pos.instrument, 0)
            if ltp > 0:
                prev_pnl = order_mgr.daily_pnl
                order_mgr.check_sl_tp(symbol, ltp)
                pnl_change = order_mgr.daily_pnl - prev_pnl
                if pnl_change != 0:
                    risk_mgr.update_pnl(pnl_change)
                    if symbol not in order_mgr.positions:
                        closed = next(
                            (t for t in reversed(order_mgr.trade_log)
                             if t["symbol"] == symbol), None
                        )
                        if closed:
                            tracker.record_trade(
                                symbol     = symbol,
                                direction  = pos.direction,
                                qty        = pos.qty,
                                entry      = pos.entry_price,
                                exit_price = closed["exit"],
                                pnl        = closed["pnl"],
                                reason     = closed["reason"],
                            )

    # 2. Risk / hours check
    can_trade, reason = risk_mgr.can_trade()
    if not can_trade:
        log.info(f"[bot] No new trades — {reason}")
    else:
        # 3. Scan watchlist
        for symbol, instrument in config.WATCHLIST.items():
            if order_mgr.has_position(symbol):
                continue

            df = get_candles(instrument, config.CANDLE_INTERVAL, days=60)
            if df is None or len(df) < 50:
                log.debug(f"[bot] {symbol}: not enough data, skipping")
                continue

            sig = generate_signal(symbol, df)
            last_signals[symbol] = sig
            log.debug(f"[bot] {symbol}: {sig.signal} | {sig.reason}")

            if sig.signal in ("BUY", "SELL"):
                log.info(f"[bot] *** {sig.signal} SIGNAL: {symbol} @ ₹{sig.price:.2f} ***")
                log.info(f"[bot]     {sig.reason}")
                order_mgr.open_position(
                    symbol      = symbol,
                    instrument  = instrument,
                    direction   = sig.signal,
                    price       = sig.price,
                    stop_loss   = sig.stop_loss,
                    take_profit = sig.take_profit,
                )

    # 4. Record P&L data point for chart
    pnl_history.append({
        "time": datetime.now().strftime("%H:%M"),
        "pnl":  round(order_mgr.daily_pnl, 2),
    })

    log.info(f"[bot] {risk_mgr.status_line()}")
    return last_signals


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    log.info("="*55)
    log.info("  StockSarthi — Upstox AI Trading Bot")
    log.info("="*55)
    log.info(f"  Mode       : {'📄 PAPER TRADING' if config.PAPER_TRADING else '💰 LIVE TRADING'}")
    log.info(f"  Capital    : ₹{config.MAX_CAPITAL:,.0f}")
    log.info(f"  Risk/trade : {config.RISK_PER_TRADE_PCT}%")
    log.info(f"  Limits     : -{config.DAILY_LOSS_LIMIT}% loss / +{config.DAILY_PROFIT_TARGET}% target")
    log.info(f"  Strategy   : EMA({config.EMA_SHORT}/{config.EMA_LONG}) + RSI({config.RSI_PERIOD}) + MACD + VWAP")
    log.info(f"  Interval   : {config.CANDLE_INTERVAL} candles")
    log.info(f"  Dashboard  : http://localhost:5000  (run python dashboard.py)")
    log.info(f"  Watchlist  : {', '.join(config.WATCHLIST.keys())}")
    log.info("="*55)

    _validate_config()

    order_mgr    = OrderManager()
    risk_mgr     = RiskManager()
    tracker      = PortfolioTracker()
    pnl_history  = []
    last_signals = {}

    send_notification(
        f"🚀 Bot started | {'PAPER' if config.PAPER_TRADING else 'LIVE'} | "
        f"Capital ₹{config.MAX_CAPITAL:,.0f}"
    )

    # Write initial state so dashboard doesn't show "offline"
    write_state(order_mgr, risk_mgr, tracker, last_signals, pnl_history)

    _wait_for_market_open()
    if not _running:
        return

    log.info("[bot] ✅ Market open — starting trading session")
    send_notification("🔔 Market open — bot is now trading!")

    squared_off = False

    while _running:
        now = datetime.now()
        sh, sm = config.SQUAREOFF_TIME
        squareoff_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)

        if now >= squareoff_dt and not squared_off:
            log.info("[bot] ⏰ 3:20 PM — squaring off all positions")
            ltp_map = _fetch_ltps(order_mgr)
            order_mgr.close_all_positions(ltp_map, "End-of-day square-off")
            squared_off = True
            write_state(order_mgr, risk_mgr, tracker, last_signals, pnl_history)
            break

        last_signals = _run_scan(order_mgr, risk_mgr, tracker, pnl_history, last_signals)

        # Write state file for dashboard to read
        write_state(order_mgr, risk_mgr, tracker, last_signals, pnl_history)

        # Sleep in 1s ticks so Ctrl+C is responsive
        for _ in range(config.SCAN_INTERVAL):
            if not _running:
                break
            time.sleep(1)

    # ── End of session ──────────────────────────────────────────────────────
    log.info("[bot] Session ended. Closing any open positions...")
    if order_mgr.positions:
        ltp_map = _fetch_ltps(order_mgr)
        order_mgr.close_all_positions(ltp_map, "Bot shutdown")

    tracker.print_summary()
    tracker.save_report()
    write_state(order_mgr, risk_mgr, tracker, last_signals, pnl_history)

    summary = tracker.stats()
    send_notification(
        f"📊 Session ended | Trades: {summary.get('total', 0)} | "
        f"P&L: ₹{summary.get('total_pnl', 0):+.2f} | "
        f"Win rate: {summary.get('win_rate', 0)}%"
    )


if __name__ == "__main__":
    main()
