"""
config.py
All bot settings loaded from .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Upstox API
API_KEY          = os.getenv("UPSTOX_API_KEY", "")
API_SECRET       = os.getenv("UPSTOX_API_SECRET", "")
REDIRECT_URI     = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8000/callback")
ACCESS_TOKEN     = os.getenv("UPSTOX_ACCESS_TOKEN", "")

# Safety
PAPER_TRADING       = os.getenv("PAPER_TRADING", "true").lower() == "true"
MAX_CAPITAL         = float(os.getenv("MAX_CAPITAL", 50000))
RISK_PER_TRADE_PCT  = float(os.getenv("RISK_PER_TRADE", 2))
DAILY_LOSS_LIMIT    = float(os.getenv("DAILY_LOSS_LIMIT", 5))
DAILY_PROFIT_TARGET = float(os.getenv("DAILY_PROFIT_TARGET", 3))

# Market hours IST
MARKET_OPEN    = (9, 15)
MARKET_CLOSE   = (15, 15)
SQUAREOFF_TIME = (15, 20)

# Strategy
EMA_SHORT        = 9
EMA_LONG         = 21
RSI_PERIOD       = 14
RSI_OVERBOUGHT   = 70
RSI_OVERSOLD     = 30
STOP_LOSS_PCT    = 1.5
TAKE_PROFIT_PCT  = 3.0
CANDLE_INTERVAL  = "30minute"
SCAN_INTERVAL    = 60

# Watchlist — NSE instrument tokens
# Full list: https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz
WATCHLIST = {
    "RELIANCE":   "NSE_EQ|INE002A01018",
    "TCS":        "NSE_EQ|INE467B01029",
    "INFY":       "NSE_EQ|INE009A01021",
    "HDFCBANK":   "NSE_EQ|INE040A01034",
    "ICICIBANK":  "NSE_EQ|INE090A01021",
    "WIPRO":      "NSE_EQ|INE075A01022",
    "SBIN":       "NSE_EQ|INE062A01020",
    "BAJFINANCE": "NSE_EQ|INE296A01024",
    "HCLTECH":    "NSE_EQ|INE860A01027",
    "AXISBANK":   "NSE_EQ|INE238A01034",
}

# Telegram alerts (optional)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
