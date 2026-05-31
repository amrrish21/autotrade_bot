"""
notifier.py — Telegram alerts (optional).

If TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set in .env,
every trade event is sent as a Telegram message.
Otherwise notifications are silently skipped.
"""

import requests
import config
from datetime import datetime


def send_notification(message: str):
    """Send a Telegram message. Fails silently if not configured."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return

    timestamp = datetime.now().strftime("%d %b %H:%M:%S")
    full_msg  = f"🤖 *Upstox Bot*\n`{timestamp}`\n\n{message}"

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    config.TELEGRAM_CHAT_ID,
        "text":       full_msg,
        "parse_mode": "Markdown",
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass   # Never let notification failure crash the bot
