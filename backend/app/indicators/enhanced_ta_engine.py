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
    """Enhanced TA-Lib for indicator calculations with support/resistance and volatility improvements"""
    if df.empty or len(df) < 50:
        return df
    
    df = df.copy()
    
    # Basic EMAs
    df['ema_20'] = ta.EMA(df['close'], timeperiod=20)
    df['ema_50'] = ta.EMA(df['close'], timeperiod=50)
    df['ema_200'] = ta.EMA(df['close'], timeperiod=200)

    # SMAs (required by swing strategy)
    df['sma_50'] = ta.SMA(df['close'], timeperiod=50)
    df['sma_200'] = ta.SMA(df['close'], timeperiod=200)

    # MACD
    macd, macd_signal, macd_hist = ta.MACD(df['close'])
    df['macd_hist'] = macd_hist

    # RSI
    df['rsi'] = ta.RSI(df['close'], timeperiod=14)

    # ATR
    df['atr'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=14)

    # Bollinger Bands
    df['bb_upper'], df['bb_mid'], df['bb_lower'] = ta.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2)

    # Support/Resistance Levels
    df['pivot_high'] = df['high'].rolling(window=5, center=True).max()
    df['pivot_low'] = df['low'].rolling(window=5, center=True).min()
    df['resistance_level'] = df['high'].rolling(window=20).max()
    df['support_level'] = df['low'].rolling(window=20).min()
    range_size = df['resistance_level'] - df['support_level']
    df['price_position'] = np.where(range_size > 0, 
                                   (df['close'] - df['support_level']) / range_size, 
                                   0.5)
    tolerance = 0.002  # 0.2% tolerance
    df['near_resistance'] = (df['close'] >= df['resistance_level'] * (1 - tolerance))
    df['near_support'] = (df['close'] <= df['support_level'] * (1 + tolerance))
    df['safe_entry_zone'] = ~(df['near_resistance'] | df['near_support'])

    # Volatility Filters
    df['atr_sma'] = ta.SMA(df['atr'], timeperiod=14)
    df['atr_ratio'] = df['atr'] / df['close']
    df['volatility_spike'] = df['atr'] > df['atr_sma'] * 1.8
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    df['bb_width_sma'] = df['bb_width'].rolling(window=20).mean()
    df['low_volatility'] = df['bb_width'] < df['bb_width_sma'] * 0.7
    df['high_volatility'] = df['bb_width'] > df['bb_width_sma'] * 1.5
    df['range_volatility'] = (df['high'] - df['low']) / df['close']
    df['range_vol_sma'] = df['range_volatility'].rolling(window=14).mean()
    df['stable_market'] = df['range_volatility'] < df['range_vol_sma'] * 1.3
    df['volatility_ok'] = (~df['volatility_spike']) & df['stable_market'] & (~df['low_volatility'])

    # 🎯 COMBINED FILTER SCORE (0-2 points)
    df['accuracy_score'] = (
        df['safe_entry_zone'].astype(int) +       # 1 point  
        df['volatility_ok'].astype(int)           # 1 point
    )

    # Supply/Demand Zones (basic)
    df['supply_zone'] = df['high'].rolling(window=30).max()
    df['demand_zone'] = df['low'].rolling(window=30).min()

    # Add existing candlestick patterns and other indicators
    df = add_candlestick_patterns(df)
    df = add_supertrend(df)
    
    return df.fillna(0)

def add_indicators_pandas(df: pd.DataFrame) -> pd.DataFrame:
    """Enhanced fallback using pandas calculations with support/resistance and volatility improvements"""
    if df.empty or len(df) < 50:
        return df
        
    df = df.copy()
    
    # Basic EMAs
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

    # RSI (simplified)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

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

    # Support/Resistance Levels
    df['pivot_high'] = df['high'].rolling(window=5, center=True).max()
    df['pivot_low'] = df['low'].rolling(window=5, center=True).min()
    df['resistance_level'] = df['high'].rolling(window=20).max()
    df['support_level'] = df['low'].rolling(window=20).min()
    
    range_size = df['resistance_level'] - df['support_level']
    df['price_position'] = np.where(range_size > 0, 
                                   (df['close'] - df['support_level']) / range_size, 
                                   0.5)
    
    tolerance = 0.002
    df['near_resistance'] = (df['close'] >= df['resistance_level'] * (1 - tolerance))
    df['near_support'] = (df['close'] <= df['support_level'] * (1 + tolerance))
    df['safe_entry_zone'] = ~(df['near_resistance'] | df['near_support'])

    # Volatility Filters
    df['atr_sma'] = df['atr'].rolling(window=14).mean()
    df['atr_ratio'] = df['atr'] / df['close']
    df['volatility_spike'] = df['atr'] > df['atr_sma'] * 1.8
    
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    df['bb_width_sma'] = df['bb_width'].rolling(window=20).mean()
    df['low_volatility'] = df['bb_width'] < df['bb_width_sma'] * 0.7
    df['high_volatility'] = df['bb_width'] > df['bb_width_sma'] * 1.5
    
    df['range_volatility'] = (df['high'] - df['low']) / df['close']
    df['range_vol_sma'] = df['range_volatility'].rolling(window=14).mean()
    df['stable_market'] = df['range_volatility'] < df['range_vol_sma'] * 1.3
    
    df['volatility_ok'] = (~df['volatility_spike']) & df['stable_market'] & (~df['low_volatility'])

    # Supply/Demand Zones (basic)
    df['supply_zone'] = df['high'].rolling(window=30).max()
    df['demand_zone'] = df['low'].rolling(window=30).min()

    # COMBINED FILTER SCORE (0-2 points) - NO VOLUME
    df['accuracy_score'] = (
        df['safe_entry_zone'].astype(int) +       # 1 point  
        df['volatility_ok'].astype(int)           # 1 point
    )

    # Add existing patterns
    df = add_candlestick_patterns(df)
    df = add_supertrend(df)
    
    return df.fillna(0)

def add_supertrend(df: pd.DataFrame, period=10, multiplier=3.0) -> pd.DataFrame:
    """Professional SuperTrend implementation"""
    hl2 = (df['high'] + df['low']) / 2
    atr = df['atr'] if 'atr' in df.columns else calculate_atr(df, period)
    
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(1, len(df)):
        # Upper band logic
        if upper_band.iloc[i] < upper_band.iloc[i-1] or df['close'].iloc[i-1] > upper_band.iloc[i-1]:
            upper_band.iloc[i] = upper_band.iloc[i]
        else:
            upper_band.iloc[i] = upper_band.iloc[i-1]
            
        # Lower band logic  
        if lower_band.iloc[i] > lower_band.iloc[i-1] or df['close'].iloc[i-1] < lower_band.iloc[i-1]:
            lower_band.iloc[i] = lower_band.iloc[i]
        else:
            lower_band.iloc[i] = lower_band.iloc[i-1]
            
        # SuperTrend calculation
        if supertrend.iloc[i-1] == upper_band.iloc[i-1] and df['close'].iloc[i] < upper_band.iloc[i]:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = -1
        elif supertrend.iloc[i-1] == lower_band.iloc[i-1] and df['close'].iloc[i] > lower_band.iloc[i]:
            supertrend.iloc[i] = lower_band.iloc[i]  
            direction.iloc[i] = 1
        elif df['close'].iloc[i] <= lower_band.iloc[i]:
            supertrend.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1
        else:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = -1
    
    df['supertrend'] = supertrend
    df['supertrend_direction'] = direction
    return df

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR) using pandas."""
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr

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

    # Add more professional patterns:
    # Doji - Indecision pattern
    df['doji'] = (body_size / candle_range < 0.1) & (candle_range > 0)
    
    # Shooting star - Bearish reversal
    df['shooting_star'] = (
        (upper_shadow > 2 * body_size) &  # Long upper shadow
        (lower_shadow < body_size * 0.3) &  # Short lower shadow
        (df['close'] < df['open'])  # Bearish body
    )
    
    # Morning star - Bullish reversal (3-candle pattern)
    df['morning_star'] = (
        (df['close'].shift(2) < df['open'].shift(2)) &  # First candle bearish
        (abs(df['close'].shift(1) - df['open'].shift(1)) < body_size.shift(1) * 0.3) &  # Middle doji
        (df['close'] > df['open']) &  # Third candle bullish
        (df['close'] > df['close'].shift(2))  # Closes above first candle
    )
    
    return df