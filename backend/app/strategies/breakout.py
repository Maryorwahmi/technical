
from app.indicators.ta_engine import add_indicators
from typing import Dict, Any
import pandas as pd

def breakout_mtf_logic(mtf_data: Dict[str, pd.DataFrame], symbol: str) -> Dict[str, Any]:
    """
    Multi-timeframe breakout strategy logic with scoring and router compatibility.
    Timeframes: M15 (entry), H1/H4 (confirmation)
    """
    m15 = add_indicators(mtf_data['M15'])
    h1 = add_indicators(mtf_data['H1'])
    h4 = add_indicators(mtf_data['H4'])
    m15_last = m15.iloc[-1]
    h1_last = h1.iloc[-1]
    h4_last = h4.iloc[-1]

    score_buy = 0
    score_sell = 0

    # M15 Bollinger breakout
    bb_upper = m15_last['bb_upper']
    bb_lower = m15_last['bb_lower']
    price = m15_last['close']
    atr = m15_last['atr']

    recent_range = m15['high'].rolling(20).max() - m15['low'].rolling(20).min()
    range_tight = recent_range.iloc[-1] < 2 * atr

    breakout_up = price > bb_upper and range_tight
    breakout_down = price < bb_lower and range_tight

    # H1/H4 volatility confirmation
    h1_atr_rising = h1['atr'].iloc[-1] > h1['atr'].iloc[-5]
    h4_atr_rising = h4['atr'].iloc[-1] > h4['atr'].iloc[-5]

    # H1/H4 trend confirmation
    h1_uptrend = h1_last['ema_20'] > h1_last['ema_50']
    h1_downtrend = h1_last['ema_20'] < h1_last['ema_50']
    h4_uptrend = h4_last['ema_20'] > h4_last['ema_50']
    h4_downtrend = h4_last['ema_20'] < h4_last['ema_50']

    # Scoring logic for BUY
    if breakout_up:
        score_buy += 1
    if h1_atr_rising:
        score_buy += 1
    if h4_atr_rising:
        score_buy += 1
    if h1_uptrend:
        score_buy += 1
    if h4_uptrend:
        score_buy += 1

    # Scoring logic for SELL
    if breakout_down:
        score_sell += 1
    if h1_atr_rising:
        score_sell += 1
    if h4_atr_rising:
        score_sell += 1
    if h1_downtrend:
        score_sell += 1
    if h4_downtrend:
        score_sell += 1

    threshold = 3  # Minimum score for signal

    def get_confidence(score):
        if score >= 4:
            return 95
        elif score == 3:
            return 80
        elif score == 2:
            return 70
        else:
            return 0

    if score_buy >= threshold:
        confidence = get_confidence(score_buy)
        return {
            "symbol": symbol,
            "strategy": "breakout",
            "timeframe": "M15",
            "direction": "BUY",
            "entry": float(price),
            "stop_loss": float(price - 1.5 * atr),
            "take_profit": float(price + 3 * atr),
            "confidence": confidence,
            "reason": f"Breakout MTF BUY score = {score_buy}"
        }
    if score_sell >= threshold:
        confidence = get_confidence(score_sell)
        return {
            "symbol": symbol,
            "strategy": "breakout",
            "timeframe": "M15",
            "direction": "SELL",
            "entry": float(price),
            "stop_loss": float(price + 1.5 * atr),
            "take_profit": float(price - 3 * atr),
            "confidence": confidence,
            "reason": f"Breakout MTF SELL score = {score_sell}"
        }
    return {}

def detect_breakout_signal(df: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
    # Legacy single-timeframe breakout logic
    df = add_indicators(df)
    last = df.iloc[-1]

    closes = df['close']
    bb_upper = last['bb_upper']
    bb_lower = last['bb_lower']
    atr = last['atr']
    price = last['close']

    recent_range = df['high'].rolling(20).max() - df['low'].rolling(20).min()
    range_tight = recent_range.iloc[-1] < 2 * atr

    breakout_up = price > bb_upper and range_tight
    breakout_down = price < bb_lower and range_tight

    if breakout_up:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": "BUY",
            "entry": float(price),
            "stop_loss": float(price - 1.5 * atr),
            "take_profit": float(price + 3 * atr),
            "confidence": 88,
            "reason": "Breakout above Bollinger Band after tight range"
        }

    if breakout_down:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": "SELL",
            "entry": float(price),
            "stop_loss": float(price + 1.5 * atr),
            "take_profit": float(price - 3 * atr),
            "confidence": 88,
            "reason": "Breakout below Bollinger Band after tight range"
        }

    return {}
