import sqlite3
from datetime import datetime
from app.core.logger import setup_logger
from app.data.mt5_client import fetch_ohlcv
from app.data.mt5_client import place_order

DB_PATH = "signals.db"
logger = setup_logger("Forecast")

def save_forecast_signal(signal: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS forecast_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        timeframe TEXT,
        direction TEXT,
        entry REAL,
        stop_loss REAL,
        take_profit REAL,
        confidence INTEGER,
        reason TEXT,
        triggered INTEGER DEFAULT 0
    )
    """)
    c.execute("""
    INSERT INTO forecast_signals (
        timestamp, symbol, timeframe, direction,
        entry, stop_loss, take_profit, confidence, reason
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        signal["symbol"],
        signal["timeframe"],
        signal["direction"],
        signal["entry"],
        signal["stop_loss"],
        signal["take_profit"],
        signal["confidence"],
        signal["reason"]
    ))
    conn.commit()
    conn.close()

def check_forecast_entries():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Ensure table exists before querying
    c.execute("""
    CREATE TABLE IF NOT EXISTS forecast_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        timeframe TEXT,
        direction TEXT,
        entry REAL,
        stop_loss REAL,
        take_profit REAL,
        confidence INTEGER,
        reason TEXT,
        triggered INTEGER DEFAULT 0
    )
    """)
    c.execute("SELECT * FROM forecast_signals WHERE triggered = 0")
    rows = c.fetchall()

    for row in rows:
        id, _, symbol, timeframe, direction, entry, sl, tp, *_ = row

        try:
            data = fetch_ohlcv(symbol, timeframe, bars=1)
            current_price = data[-1]['close']

            if direction == "BUY" and current_price <= entry:
                logger.info(f"Executing forecast BUY for {symbol} at {entry}")
                success = place_order(symbol, direction, entry, sl, tp)
                if success:
                    c.execute("UPDATE forecast_signals SET triggered = 1 WHERE id = ?", (id,))
            elif direction == "SELL" and current_price >= entry:
                logger.info(f"Executing forecast SELL for {symbol} at {entry}")
                success = place_order(symbol, direction, entry, sl, tp)
                if success:
                    c.execute("UPDATE forecast_signals SET triggered = 1 WHERE id = ?", (id,))
        except Exception as e:
            logger.error(f"Error checking forecast for {symbol}: {e}")

    conn.commit()
    conn.close()
