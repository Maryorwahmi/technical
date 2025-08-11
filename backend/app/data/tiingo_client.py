import requests
import pandas as pd
from datetime import datetime, timedelta
from app.core.logger import setup_logger
from typing import List, Dict, Any
import time

logger = setup_logger("TiingoClient")

# Tiingo API Keys with rate limits
TIINGO_API_KEYS = [
    "821f3e1f64f3b7f43dbae99026569fcdf51b2dd6",  # 1d
    "095183391b68605973586b38e9035cc188639e01",  # 1h
    "e6f30c8c089059faa5b059385c01c90132dcb7b5",  # 4h
    "6ca4d2bbe08bf4557a4bc8fec4924f321858672f", # 15m
]

# Map timeframes to appropriate API keys
TIMEFRAME_API_MAP = {
    "M15": TIINGO_API_KEYS[3],  # 15m key
    "H1": TIINGO_API_KEYS[1],   # 1h key  
    "H4": TIINGO_API_KEYS[2],   # 4h key
    "D1": TIINGO_API_KEYS[0],   # 1d key
}

# Map our timeframes to Tiingo frequencies
TIMEFRAME_FREQ_MAP = {
    "M15": "15min",
    "H1": "1hour", 
    "H4": "4hour",
    "D1": "1day"
}

def fetch_tiingo_forex(symbol: str, timeframe: str, bars: int = 250) -> List[Dict[str, Any]]:
    """
    Fetch forex data from Tiingo API
    """
    try:
        api_keys = TIINGO_API_KEYS.copy()
        api_key_idx = 0
        frequency = TIMEFRAME_FREQ_MAP.get(timeframe, "1hour")
        tiingo_symbol = symbol.lower()
        end_date = datetime.now()
        if timeframe == "M15":
            start_date = end_date - timedelta(hours=bars * 0.25)
        elif timeframe == "H1":
            start_date = end_date - timedelta(hours=bars)
        elif timeframe == "H4":
            bars = max(bars, 400)
            start_date = end_date - timedelta(hours=bars * 4)
        elif timeframe == "D1":
            start_date = end_date - timedelta(days=bars)
        else:
            start_date = end_date - timedelta(hours=bars)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        url = f"https://api.tiingo.com/tiingo/fx/{tiingo_symbol}/prices"
        params = {
            "token": api_keys[api_key_idx],
            "startDate": start_str,
            "endDate": end_str,
            "resampleFreq": frequency,
            "format": "json"
        }
        logger.info(f"Fetching {symbol} {timeframe} data from Tiingo...")
        while api_key_idx < len(api_keys):
            params["token"] = api_keys[api_key_idx]
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 429:
                logger.warning(f"Tiingo API rate limit hit for key {api_keys[api_key_idx]}. Rotating key...")
                api_key_idx += 1
                time.sleep(1)
                continue
            elif response.status_code == 200:
                data = response.json()
                if not data:
                    logger.warning(f"No data returned from Tiingo for {symbol}")
                    return []
                ohlcv_data = []
                for item in data:
                    try:
                        timestamp = pd.to_datetime(item['date']).timestamp()
                        ohlcv_data.append({
                            'time': int(timestamp),
                            'open': float(item['open']),
                            'high': float(item['high']),
                            'low': float(item['low']),
                            'close': float(item['close']),
                            'tick_volume': int(item.get('volume', 1000)),
                            'spread': 2,
                            'real_volume': 0
                        })
                    except (KeyError, ValueError, TypeError) as e:
                        logger.warning(f"Error parsing Tiingo data point: {e}")
                        continue
                logger.info(f"Successfully fetched {len(ohlcv_data)} bars from Tiingo for {symbol} {timeframe}")
                return ohlcv_data[-bars:] if len(ohlcv_data) > bars else ohlcv_data
            else:
                logger.error(f"Tiingo API error: {response.status_code} - {response.text}")
                return []
        logger.error(f"All Tiingo API keys exhausted or rate limited for {symbol} {timeframe}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching from Tiingo: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching from Tiingo: {e}")
        return []

def get_available_symbols() -> List[str]:
    """
    Return list of available forex symbols
    """
    return ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD"]
