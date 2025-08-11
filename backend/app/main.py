from fastapi import FastAPI
import warnings
import pandas as pd
import numpy as np

# Suppress specific pandas FutureWarnings about fillna method deprecation
warnings.filterwarnings("ignore", message=".*fillna with 'method' is deprecated.*", category=FutureWarning)

# Suppress pkg_resources deprecation warning from pandas-ta
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*", category=UserWarning)

from app.core.config import settings
from app.data.mt5_client import initialize_mt5, shutdown_mt5, fetch_ohlcv
from app.strategies.trend import detect_trend_signal
from app.signals.signal_engine import run_all_strategies
from app.database.db_utils import init_db
from app.scheduler.jobs import start_scheduler

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

@app.on_event("startup")
def startup_event():
    init_db()
    initialize_mt5()
    start_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    shutdown_mt5()

@app.get("/fetch/{symbol}/{timeframe}")
def get_ohlcv(symbol: str, timeframe: str):
    try:
        data = fetch_ohlcv(symbol.upper(), timeframe.upper(), bars=100)
        return {"symbol": symbol, "timeframe": timeframe, "bars": len(data)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/signal/trend/{symbol}/{timeframe}")
def trend_signal(symbol: str, timeframe: str):
    try:
        raw = fetch_ohlcv(symbol.upper(), timeframe.upper(), bars=150)
        df = pd.DataFrame(raw)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        signal = detect_trend_signal(df, symbol, timeframe)
        return signal if signal else {"signal": "No valid trend signal"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/scan/{symbol}/{timeframe}")
def scan_market(symbol: str, timeframe: str):
    try:
        raw = fetch_ohlcv(symbol.upper(), timeframe.upper(), bars=150)
        df = pd.DataFrame(raw)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        # Signal engine handles all saving internally
        signals = run_all_strategies(df, symbol, timeframe)

        return signals if signals else {"signal": "No high-confidence signals"}
    except Exception as e:
        return {"error": str(e)}