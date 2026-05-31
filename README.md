# StockSarthi — Upstox AI Auto Trading Bot

Fully automated NSE/BSE intraday trading bot for Upstox.
Trades while you attend class, sleep, or are offline.

---

## Features

- EMA crossover + RSI + MACD + VWAP strategy
- Auto stop-loss and take-profit on every trade
- Daily loss limit and profit target auto-halt
- Mandatory 3:20 PM square-off (NSE intraday rule)
- Risk-based position sizing (never over-exposes capital)
- Paper trading mode (default — no real money)
- Backtester to test strategy on historical data
- Telegram alerts for every trade event
- Daily report saved as JSON + CSV

---

## Project Structure

```
upstox_bot/
├── .env.example        ← copy to .env and fill credentials
├── requirements.txt    ← pip install -r requirements.txt
├── auth.py             ← Step 1: generate access token
├── bot.py              ← Step 2: run the trading bot
├── backtest.py         ← test strategy offline
├── config.py           ← all settings in one place
├── market_data.py      ← fetch candles + LTP from Upstox API
├── indicators.py       ← EMA, RSI, MACD, VWAP, Bollinger Bands
├── strategy.py         ← signal generation logic
├── order_manager.py    ← place / track / close orders
├── risk_manager.py     ← daily P&L limits and market hours
├── portfolio_tracker.py← trade log + daily report
├── notifier.py         ← Telegram alerts
├── logger.py           ← coloured console + file logging
├── logs/               ← auto-created daily log files
└── reports/            ← auto-created daily JSON + CSV reports
```

---

## Quick Start

### 1. Install Python (3.10+)
Download from https://python.org

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Get Upstox API credentials
1. Go to https://developer.upstox.com
2. Log in with your Upstox trading account
3. Click "Create App"
4. Fill in any app name
5. Set Redirect URL to: `http://localhost:8000/callback`
6. Copy your **API Key** and **API Secret**

### 4. Configure the bot
```bash
cp .env.example .env
```
Open `.env` in any text editor and fill in:
```
UPSTOX_API_KEY=your_actual_api_key
UPSTOX_API_SECRET=your_actual_api_secret
UPSTOX_REDIRECT_URI=http://localhost:8000/callback
```

### 5. Generate access token (do this every trading day)
```bash
python auth.py
```
- Open the printed URL in your browser
- Log in to Upstox and authorize the app
- Copy the `code` from the redirect URL
```bash
python auth.py PASTE_CODE_HERE
```
Token is saved to `.env` automatically.

### 6. (Optional) Run backtest first
```bash
python backtest.py
```
See how the strategy would have performed over the last 90 days.

### 7. Start the bot (paper mode by default)
```bash
python bot.py
```
The bot waits for 9:15 AM, then starts scanning and trading.
Press `Ctrl+C` at any time to stop gracefully.

### 8. Switch to live trading
Open `.env` and change:
```
PAPER_TRADING=false
```
⚠️ Only do this after testing in paper mode for at least 2 weeks.

---

## Telegram Alerts (Optional)

1. Message @BotFather on Telegram → create a bot → copy token
2. Message @userinfobot to get your chat ID
3. Add to `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## Strategy Logic

**BUY signal** — all 4 conditions must be true:
- EMA 9 crosses **above** EMA 21 (bullish crossover)
- RSI is between 30 and 70 (not extreme)
- MACD histogram is **positive** (bullish momentum)
- Price is **above** VWAP (intraday trend up)

**SELL/EXIT signal** — all 4 conditions must be true:
- EMA 9 crosses **below** EMA 21 (bearish crossover)
- RSI is between 30 and 60
- MACD histogram is **negative**
- Price is **below** VWAP

**Auto exit:**
- Stop-loss: 1.5% below entry
- Take-profit: 3.0% above entry
- 3:20 PM: all positions force-closed

---

## Risk Settings (in .env)

| Setting | Default | Meaning |
|---|---|---|
| MAX_CAPITAL | 50000 | Total capital the bot can use (INR) |
| RISK_PER_TRADE | 2 | Risk 2% of capital per trade |
| DAILY_LOSS_LIMIT | 5 | Stop trading if down 5% on the day |
| DAILY_PROFIT_TARGET | 3 | Stop trading after 3% profit |
| PAPER_TRADING | true | Simulated trades — no real money |

---

## Watchlist

Edit `config.py` to add/remove stocks. Find instrument tokens at:
https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz

Format: `"NSE_EQ|<ISIN>"`

---

## Important Warnings

- **Start with PAPER_TRADING=true** — run for 2+ weeks before going live
- Algo trading carries real financial risk — never trade money you can't afford to lose
- Past backtest performance does not guarantee future returns
- The bot must run on a computer/server that stays connected during market hours
- Run `python auth.py` every morning before 9:15 AM to refresh the access token
- This bot is for educational purposes — you are responsible for your own trades

---

## Daily Routine

```
8:45 AM  →  python auth.py         (refresh token)
             python auth.py <code>
9:10 AM  →  python bot.py          (bot waits for 9:15 AM open)
3:25 PM  →  bot auto-closes all positions and prints report
```
