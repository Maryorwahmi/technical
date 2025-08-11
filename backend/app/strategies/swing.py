
from app.indicators.ta_engine import add_indicators
from typing import Dict, Any
import pandas as pd

def swing_mtf_logic(mtf_data: Dict[str, pd.DataFrame], symbol: str) -> Dict[str, Any]:
    """
    Multi-timeframe swing strategy logic with scoring and router compatibility.
    Timeframes: M15 (entry), H1 (confirmation)
    """
    m15 = add_indicators(mtf_data['M15'])
    h1 = add_indicators(mtf_data['H1'])
    m15_last = m15.iloc[-1]
    h1_last = h1.iloc[-1]

    score_buy = 0
    score_sell = 0

    # M15 oversold/overbought
    m15_oversold = m15_last['rsi'] < 30
    m15_overbought = m15_last['rsi'] > 70

    # M15 Stochastic cross
    m15_stoch_cross_up = m15['stoch_k'].iloc[-2] < m15['stoch_d'].iloc[-2] and m15_last['stoch_k'] > m15_last['stoch_d']
    m15_stoch_cross_down = m15['stoch_k'].iloc[-2] > m15['stoch_d'].iloc[-2] and m15_last['stoch_k'] < m15_last['stoch_d']

    # M15 Candle confirmation
    m15_bull_candle = m15_last['bullish_engulfing'] or m15_last['hammer']
    m15_bear_candle = m15_last['bearish_engulfing']

    # H1 trend filter
    h1_uptrend = h1_last['sma_50'] > h1_last['sma_200']
    h1_downtrend = h1_last['sma_50'] < h1_last['sma_200']

    # Scoring logic for BUY
    if m15_oversold:
        score_buy += 1
    if m15_stoch_cross_up:
        score_buy += 1
    if m15_bull_candle:
        score_buy += 1
    if h1_uptrend:
        score_buy += 1

    # Scoring logic for SELL
    if m15_overbought:
        score_sell += 1
    if m15_stoch_cross_down:
        score_sell += 1
    if m15_bear_candle:
        score_sell += 1
    if h1_downtrend:
        score_sell += 1

    entry_price = m15_last['close']
    atr = m15_last['atr']

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
            "strategy": "swing",
            "timeframe": "M15",
            "direction": "BUY",
            "entry": float(entry_price),
            "stop_loss": float(entry_price - 1.2 * atr),
            "take_profit": float(entry_price + 2.4 * atr),
            "confidence": confidence,
            "reason": f"Swing MTF BUY score = {score_buy}"
        }
    if score_sell >= threshold:
        confidence = get_confidence(score_sell)
        return {
            "symbol": symbol,
            "strategy": "swing",
            "timeframe": "M15",
            "direction": "SELL",
            "entry": float(entry_price),
            "stop_loss": float(entry_price + 1.2 * atr),
            "take_profit": float(entry_price - 2.4 * atr),
            "confidence": confidence,
            "reason": f"Swing MTF SELL score = {score_sell}"
        }
    return {}

def detect_swing_signal(df: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
    # Legacy single-timeframe swing logic
    df = add_indicators(df)
    last = df.iloc[-1]

    oversold = last['rsi'] < 30
    overbought = last['rsi'] > 70

    stoch_cross_up = df['stoch_k'].iloc[-2] < df['stoch_d'].iloc[-2] and last['stoch_k'] > last['stoch_d']
    stoch_cross_down = df['stoch_k'].iloc[-2] > df['stoch_d'].iloc[-2] and last['stoch_k'] < last['stoch_d']

    bull_candle = last['bullish_engulfing'] or last['hammer']
    bear_candle = last['bearish_engulfing']

    price = last['close']
    atr = last['atr']

    if oversold and stoch_cross_up and bull_candle:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": "BUY",
            "entry": float(price),
            "stop_loss": float(price - 1.5 * atr),
            "take_profit": float(price + 3 * atr),
            "confidence": 90,
            "reason": "Swing reversal – RSI oversold + Stochastic cross + bullish candle"
        }

    if overbought and stoch_cross_down and bear_candle:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": "SELL",
            "entry": float(price),
            "stop_loss": float(price + 1.5 * atr),
            "take_profit": float(price - 3 * atr),
            "confidence": 90,
            "reason": "Swing reversal – RSI overbought + Stochastic cross + bearish candle"
        }

    return {}