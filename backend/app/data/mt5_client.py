def get_account_balance():
    import MetaTrader5 as mt5
    account = mt5.account_info()
    return account.balance if account else 0
from app.core.config import settings
from app.core.logger import setup_logger
from app.data.tiingo_client import fetch_tiingo_forex
import MetaTrader5 as mt5
from datetime import datetime
import time
import logging
import pandas as pd

logger = setup_logger("MT5Client")

def initialize_mt5():
    from app.core.config import settings
    try:
        if not mt5.initialize(login=settings.MT5_LOGIN, password=settings.MT5_PASSWORD, server=settings.MT5_SERVER):
            logger.error(f"MT5 initialize failed: {mt5.last_error()}")
            return False
        logger.info("MT5 initialized successfully")
        return True
    except Exception as e:
        logger.error(f"MT5 initialization error: {e}")
        return False

def shutdown_mt5():
    try:
        mt5.shutdown()
        logger.info("MT5 shutdown")
    except Exception as e:
        logger.error(f"MT5 shutdown error: {e}")

def fetch_ohlcv(symbol: str, timeframe: str, bars: int = 100):
    if timeframe not in ["M15", "H1", "H4", "D1"]:
        raise ValueError("Unsupported timeframe")

    min_bars = max(bars, 250)

    # Try MT5 first for real-time prices
    try:
        from app.core.config import settings
        
        # Initialize MT5 for this request if not already initialized
        if not mt5.initialize(login=settings.MT5_LOGIN, password=settings.MT5_PASSWORD, server=settings.MT5_SERVER):
            logger.error("MT5 initialize failed, falling back to Tiingo")
        else:
            # Map timeframe to MT5 constants
            tf_map = {
                "M15": mt5.TIMEFRAME_M15,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            
            rates = mt5.copy_rates_from_pos(symbol, tf_map[timeframe], 0, min_bars)
            if rates is not None and len(rates) > 0:
                logger.info(f"Fetched {len(rates)} bars from MT5 for {symbol} {timeframe}")
                # Convert MT5 rates to expected format
                ohlcv_data = []
                for r in rates:
                    ohlcv_data.append({
                        'time': int(r['time']),
                        'open': float(r['open']),
                        'high': float(r['high']),
                        'low': float(r['low']),
                        'close': float(r['close']),
                        'tick_volume': int(r['tick_volume']),
                        'spread': 2,
                        'real_volume': int(r['real_volume']) if 'real_volume' in r.dtype.names else 0
                    })
                mt5.shutdown()
                return ohlcv_data
            mt5.shutdown()
    except Exception as e:
        logger.error(f"MT5 error: {e}")

    # Fallback to Tiingo if MT5 fails
    logger.info(f"Fetching {symbol} {timeframe} data from Tiingo")
    tiingo_data = fetch_tiingo_forex(symbol, timeframe, min_bars)
    if tiingo_data and len(tiingo_data) > 0:
        logger.info(f"Fetched {len(tiingo_data)} bars from Tiingo for {symbol} {timeframe}")
        return tiingo_data
    logger.warning(f"Tiingo failed for {symbol} {timeframe}, using mock trending data")
    return generate_mock_trending_data(symbol, min_bars)

def generate_mock_trending_data(symbol: str, bars: int):
    """Generate trending mock data as final fallback"""
    import numpy as np
    import pandas as pd
    from datetime import datetime
    
    base_price = 1.0850 if symbol == "EURUSD" else 1.2500
    dates = pd.date_range(end=datetime.now(), periods=bars, freq='H')
    
    mock_data = []
    trend_direction = 1  # 1 for uptrend, -1 for downtrend
    
    for i, date in enumerate(dates):
        # Create a trending pattern with some noise
        trend_strength = 0.00001 * i * trend_direction
        noise = np.random.normal(0, 0.00005)
        price = base_price + trend_strength + noise
        
        # Add some intraday volatility
        high_offset = abs(np.random.normal(0, 0.0002))
        low_offset = abs(np.random.normal(0, 0.0002))
        
        open_price = price + np.random.normal(0, 0.00002)
        close_price = price + np.random.normal(0, 0.00002)
        high_price = max(open_price, close_price) + high_offset
        low_price = min(open_price, close_price) - low_offset
        
        mock_data.append({
            'time': int(date.timestamp()),
            'open': round(open_price, 5),
            'high': round(high_price, 5),
            'low': round(low_price, 5),
            'close': round(close_price, 5),
            'tick_volume': np.random.randint(100, 1000),
            'spread': 2,
            'real_volume': 0
        })
    
    logger.info(f"Generated {len(mock_data)} trending mock data points for {symbol}")
    return mock_data

def place_order(symbol, direction, entry, sl, tp, lot=0.1, magic=123456):
    # Ensure MT5 is initialized and connected
    from app.core.config import settings
    
    if not mt5.initialize():
        logger.error("MT5 initialization failed")
        return False
    
    # Login if credentials are available
    if settings.MT5_LOGIN and settings.MT5_PASSWORD and settings.MT5_SERVER:
        if not mt5.login(settings.MT5_LOGIN, password=settings.MT5_PASSWORD, server=settings.MT5_SERVER):
            logger.error(f"MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False
    
    try:
        # Get symbol info and check visibility
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.warning(f"{symbol} not found")
            return False
        
        if not symbol_info.visible:
            # Try to enable symbol in Market Watch
            if not mt5.symbol_select(symbol, True):
                logger.warning(f"Failed to select {symbol}")
                return False
            # Refresh symbol info
            symbol_info = mt5.symbol_info(symbol)

        # Check if symbol is still not visible
        if not symbol_info.visible:
            logger.warning(f"{symbol} not available or not visible")
            return False

        # Market Order (Immediate Execution)
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"Failed to get tick data for {symbol}")
            return False
        
        price = tick.ask if direction == "BUY" else tick.bid

        # 🔧 Smart filling mode detection - Try multiple filling modes for compatibility
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Failed to get symbol info for {symbol}")
            return False
            
        # Determine the best filling mode based on symbol properties
        filling_modes = []
        if symbol_info.filling_mode & 1:  # FOK supported
            filling_modes.append(mt5.ORDER_FILLING_FOK)
        if symbol_info.filling_mode & 2:  # IOC supported  
            filling_modes.append(mt5.ORDER_FILLING_IOC)
        if symbol_info.filling_mode & 4:  # RETURN supported
            filling_modes.append(mt5.ORDER_FILLING_RETURN)
            
        if not filling_modes:
            filling_modes = [mt5.ORDER_FILLING_FOK]  # Fallback
            
        logger.info(f"Available filling modes for {symbol}: {filling_modes}")
        
        # Try each filling mode until one works
        for filling_mode in filling_modes:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": magic,
                "comment": f"AutoTrade by ForexAnalyzer",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }
            
            # Add SL/TP if provided
            if sl and sl > 0:
                request["sl"] = sl
            if tp and tp > 0:
                request["tp"] = tp

            logger.info(f"Placing {direction} order for {symbol}: Lot={lot}, Price={price:.5f}, SL={sl:.5f}, TP={tp:.5f}, Filling={filling_mode}")
            
            # Send the trading request
            result = mt5.order_send(request)
            
            if result is not None:
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"✅ Order executed successfully with filling mode {filling_mode}: {result}")
                    return True
                elif result.retcode == 10030:  # Unsupported filling mode
                    logger.warning(f"⚠️ Filling mode {filling_mode} not supported for {symbol}, trying next...")
                    continue  # Try next filling mode
                else:
                    logger.error(f"Order failed with filling mode {filling_mode}: {result.retcode} | {result.comment}")
            else:
                logger.error(f"Order send returned None with filling mode {filling_mode}")
                
        # If we get here, all filling modes failed
        logger.error(f"❌ All filling modes failed for {symbol}")
        return False
        
    except Exception as e:
        logger.error(f"Order execution error: {e}")
        return False
    finally:
        mt5.shutdown()

# Add connection resilience

def ensure_mt5_connection():
    """Ensure robust MT5 connection with retries"""
    max_retries = 3
    for attempt in range(max_retries):
        if mt5.initialize():
            return True
        logger.warning(f"MT5 connection attempt {attempt + 1} failed")
        time.sleep(2)
    
    logger.error("MT5 connection failed after all retries")
    return False

def get_timeframe_minutes(timeframe):
    """Map MT5 timeframe constants to minute intervals."""
    # Accept both string and MT5 constant
    if isinstance(timeframe, str):
        tf_map = {
            "M1": 1,
            "M5": 5,
            "M15": 15,
            "M30": 30,
            "H1": 60,
            "H4": 240,
            "D1": 1440
        }
        return tf_map.get(timeframe, 1)
    # If it's an MT5 constant
    tf_const_map = {
        getattr(mt5, "TIMEFRAME_M1", None): 1,
        getattr(mt5, "TIMEFRAME_M5", None): 5,
        getattr(mt5, "TIMEFRAME_M15", None): 15,
        getattr(mt5, "TIMEFRAME_M30", None): 30,
        getattr(mt5, "TIMEFRAME_H1", None): 60,
        getattr(mt5, "TIMEFRAME_H4", None): 240,
        getattr(mt5, "TIMEFRAME_D1", None): 1440
    }
    return tf_const_map.get(timeframe, 1)

def fetch_ohlcv_robust(symbol, timeframe, count=250):
    """Robust data fetching with retries and validation"""
    if not ensure_mt5_connection():
        raise Exception("MT5 connection unavailable")
    
    # Get data with validation
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    
    if rates is None or len(rates) < 50:
        logger.warning(f"Insufficient data for {symbol}: {len(rates) if rates is not None else 0} bars")
        return None
        
    # Validate data quality
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Check for data gaps
    expected_interval = get_timeframe_minutes(timeframe)
    time_diffs = df['time'].diff().dt.total_seconds() / 60
    large_gaps = time_diffs > expected_interval * 2
    
    if large_gaps.sum() > 5:
        logger.warning(f"{symbol} has {large_gaps.sum()} large data gaps")
    
    return df
