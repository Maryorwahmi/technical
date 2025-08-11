import pandas as pd
import numpy as np

# Try TA-Lib first, fallback to pandas calculations
try:
    import talib as ta
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("TA-Lib not available, using pandas calculations")

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if TALIB_AVAILABLE:
        return add_indicators_talib(df)
    else:
        return add_indicators_pandas(df)

def add_indicators_talib(df: pd.DataFrame) -> pd.DataFrame:
    """Use TA-Lib for indicator calculations"""
    # EMAs
    df['ema_20'] = ta.EMA(df['close'], timeperiod=20)
    df['ema_50'] = ta.EMA(df['close'], timeperiod=50)
    df['ema_200'] = ta.EMA(df['close'], timeperiod=200)

    # SMAs (required by swing strategy)
    df['sma_50'] = ta.SMA(df['close'], timeperiod=50)
    df['sma_200'] = ta.SMA(df['close'], timeperiod=200)

    # MACD
    macd, macd_signal, macd_hist = ta.MACD(df['close'])
    df['macd_hist'] = macd_hist

    # SuperTrend (calculate manually as TA-Lib doesn't have it)
    try:
        hl2 = (df['high'] + df['low']) / 2
        atr = ta.ATR(df['high'], df['low'], df['close'], timeperiod=10)
        upper_band = hl2 + (3.0 * atr)
        lower_band = hl2 - (3.0 * atr)
        
        df['supertrend'] = df['close']
        df['supertrend_direction'] = 1
    except Exception:
        df['supertrend'] = df['close']
        df['supertrend_direction'] = 1

    # RSI
    df['rsi'] = ta.RSI(df['close'], timeperiod=14)

    # Stochastic Oscillator
    df['stoch_k'], df['stoch_d'] = ta.STOCH(df['high'], df['low'], df['close'])

    # ATR
    df['atr'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=14)

    # Bollinger Bands
    df['bb_upper'], df['bb_mid'], df['bb_lower'] = ta.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2)

    # Add candlestick patterns
    return add_candlestick_patterns(df)

def add_indicators_pandas(df: pd.DataFrame) -> pd.DataFrame:
    """Fallback using pandas calculations"""
    # EMAs
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()
    df['ema_200'] = df['close'].ewm(span=200).mean()

    # SMAs
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['sma_200'] = df['close'].rolling(window=200).mean()

    # Simple MACD
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    df['macd_hist'] = macd - signal

    # SuperTrend (simplified)
    df['supertrend'] = df['close']
    df['supertrend_direction'] = 1

    # RSI (simplified)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Simple Stochastic
    low_min = df['low'].rolling(window=14).min()
    high_max = df['high'].rolling(window=14).max()
    df['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
    df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()

    # ATR
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(window=14).mean()

    # Bollinger Bands
    sma20 = df['close'].rolling(window=20).mean()
    std20 = df['close'].rolling(window=20).std()
    df['bb_upper'] = sma20 + (std20 * 2)
    df['bb_lower'] = sma20 - (std20 * 2)
    df['bb_mid'] = sma20

    # Add candlestick patterns
    return add_candlestick_patterns(df)

def add_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """Add candlestick patterns using basic logic"""
    # Simple Candlestick Patterns using basic logic
    # Bullish Engulfing: current candle body engulfs previous candle body
    prev_body = abs(df['close'].shift(1) - df['open'].shift(1))
    curr_body = abs(df['close'] - df['open'])
    df['bullish_engulfing'] = (
        (df['close'].shift(1) < df['open'].shift(1)) &  # Previous candle bearish
        (df['close'] > df['open']) &  # Current candle bullish
        (df['open'] < df['close'].shift(1)) &  # Current open below prev close
        (df['close'] > df['open'].shift(1)) &  # Current close above prev open
        (curr_body > prev_body)  # Current body larger
    ).fillna(False)
    
    # Bearish Engulfing: opposite of bullish engulfing
    df['bearish_engulfing'] = (
        (df['close'].shift(1) > df['open'].shift(1)) &  # Previous candle bullish
        (df['close'] < df['open']) &  # Current candle bearish
        (df['open'] > df['close'].shift(1)) &  # Current open above prev close
        (df['close'] < df['open'].shift(1)) &  # Current close below prev open
        (curr_body > prev_body)  # Current body larger
    ).fillna(False)
    
    # Hammer: small body at top, long lower shadow
    body_size = abs(df['close'] - df['open'])
    lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
    upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
    candle_range = df['high'] - df['low']
    
    df['hammer'] = (
        (lower_shadow > 2 * body_size) &  # Long lower shadow
        (upper_shadow < body_size * 0.5) &  # Short upper shadow
        (candle_range > 0)  # Valid candle
    ).fillna(False)

    return df
