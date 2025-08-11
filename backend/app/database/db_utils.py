import sqlite3
from datetime import datetime

DB_PATH = "signals.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        timeframe TEXT,
        direction TEXT,
        entry REAL,
        stop_loss REAL,
        take_profit REAL,
        confidence INTEGER,
        reason TEXT
    )
    """)
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
    CREATE TABLE IF NOT EXISTS trade_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        direction TEXT,
        entry_price REAL,
        stop_loss REAL, 
        take_profit REAL,
        confidence INTEGER,
        execution_time TEXT,
        spread REAL,
        slippage REAL,
        status TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()
def signal_exists(symbol: str, timeframe: str, direction: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    SELECT COUNT(*) FROM signals
    WHERE symbol = ? AND timeframe = ? AND direction = ?
      AND timestamp >= datetime('now', '-1 hour')
    """, (symbol, timeframe, direction))
    count = c.fetchone()[0]
    conn.close()
    return count > 0


def save_signal(signal: dict):
    if signal_exists(signal["symbol"], signal["timeframe"], signal["direction"]):
        return  # Skip duplicate alert

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    INSERT INTO signals (timestamp, symbol, timeframe, direction, entry, stop_loss, take_profit, confidence, reason)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        signal["symbol"],
        signal["timeframe"],
        signal["direction"],
        signal["entry"],
        signal["stop_loss"],
        signal["take_profit"],
        signal.get("confidence", 0),
        signal["reason"]
    ))
    conn.commit()
    conn.close()

def save_forecast_signal(signal: dict):
    """
    Save a forecast/pending signal to the forecast_signals table.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    INSERT INTO forecast_signals (timestamp, symbol, timeframe, direction, entry, stop_loss, take_profit, confidence, reason)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        signal["symbol"],
        signal["timeframe"],
        signal["direction"],
        signal["entry"],
        signal["stop_loss"],
        signal["take_profit"],
        signal.get("confidence", 0),
        signal["reason"]
    ))
    conn.commit()
    conn.close()

# Add performance tracking
def save_trade_performance(signal, execution_result):
    """Track trade performance for optimization"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            direction TEXT,
            entry_price REAL,
            stop_loss REAL, 
            take_profit REAL,
            confidence INTEGER,
            execution_time TEXT,
            spread REAL,
            slippage REAL,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        INSERT INTO trade_performance (symbol, direction, entry_price, stop_loss, take_profit, 
                                     confidence, execution_time, spread, slippage, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        signal['symbol'], signal['direction'], signal['entry'], 
        signal['stop_loss'], signal['take_profit'], signal['confidence'],
        execution_result.get('execution_time'), execution_result.get('spread'),
        execution_result.get('slippage'), execution_result.get('status', 'unknown')
    ))
    
    conn.commit()
    conn.close()
