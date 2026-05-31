"""
market_data.py — Fetch OHLCV candles and live quotes from Upstox API.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import config
from logger import log


BASE_URL = "https://api.upstox.com/v2"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.ACCESS_TOKEN}",
        "Accept":        "application/json",
    }


def get_candles(instrument_token: str, interval: str = None,
                days: int = 60) -> Optional[pd.DataFrame]:
    """
    Fetch historical OHLCV candles for an instrument.

    Returns a DataFrame with columns: timestamp, open, high, low, close, volume
    Returns None on failure.
    """
    interval = interval or config.CANDLE_INTERVAL
    to_date   = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Map interval to Upstox API path segment
    interval_map = {
        "1minute":   "1minute",
        "5minute":   "5minute",
        "15minute":  "15minute",
        "30minute":  "30minute",
        "60minute":  "60minute",
        "day":       "day",
        "week":      "week",
        "month":     "month",
    }
    api_interval = interval_map.get(interval, "30minute")

    # Encode the token for the URL (pipe → %7C)
    token_enc = instrument_token.replace("|", "%7C")
    url = (
        f"{BASE_URL}/historical-candle/{token_enc}"
        f"/{api_interval}/{to_date}/{from_date}"
    )

    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()

        candles = data.get("data", {}).get("candles", [])
        if not candles:
            log.warning(f"No candles returned for {instrument_token}")
            return None

        df = pd.DataFrame(candles,
                          columns=["timestamp", "open", "high", "low",
                                   "close", "volume", "oi"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        df[["open", "high", "low", "close", "volume"]] = \
            df[["open", "high", "low", "close", "volume"]].astype(float)
        return df

    except requests.HTTPError as e:
        log.error(f"HTTP error fetching candles for {instrument_token}: {e.response.text}")
    except Exception as e:
        log.error(f"Error fetching candles for {instrument_token}: {e}")
    return None


def get_ltp(instrument_tokens: list) -> dict:
    """
    Fetch Last Traded Price for a list of instrument tokens.
    Returns dict: { instrument_token: ltp_float }
    """
    tokens_param = ",".join(instrument_tokens)
    url = f"{BASE_URL}/market-quote/ltp"
    params = {"instrument_key": tokens_param}

    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        result = {}
        for token, info in data.items():
            ltp = info.get("last_price", 0.0)
            result[token] = float(ltp)
        return result

    except requests.HTTPError as e:
        log.error(f"HTTP error fetching LTP: {e.response.text}")
    except Exception as e:
        log.error(f"Error fetching LTP: {e}")
    return {}


def get_quote(instrument_token: str) -> Optional[dict]:
    """
    Fetch full market quote (bid, ask, OHLC, volume, etc.) for one instrument.
    """
    token_enc = instrument_token.replace("|", "%7C")
    url = f"{BASE_URL}/market-quote/quotes"
    params = {"instrument_key": instrument_token}

    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return data.get(instrument_token.replace("|", "_"), None)
    except Exception as e:
        log.error(f"Error fetching quote for {instrument_token}: {e}")
    return None
