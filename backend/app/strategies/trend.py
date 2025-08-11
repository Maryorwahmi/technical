from app.indicators.ta_engine import add_indicators
import pandas as pd
from typing import Dict, Any

def trend_mtf_logic(mtf_data: Dict[str, pd.DataFrame], symbol: str) -> Dict[str, Any]:
    d1 = add_indicators(mtf_data['D1'])
    h4 = add_indicators(mtf_data['H4'])
    h1 = add_indicators(mtf_data['H1'])
    m15 = add_indicators(mtf_data['M15'])

    d1_last = d1.iloc[-1]
    h4_last = h4.iloc[-1]
    h1_last = h1.iloc[-1]
    m15_last = m15.iloc[-1]

    score_buy = 0
    score_sell = 0

    # D1 trend filter
    d1_uptrend = d1_last['ema_20'] > d1_last['ema_50']
    d1_downtrend = d1_last['ema_20'] < d1_last['ema_50']
    d1_trend_ok = abs(d1_last['ema_20'] - d1_last['ema_50']) / d1_last['close'] > 0.002
    if not d1_trend_ok:
        return {}

    # H4 structure
    h4_up = h4_last['ema_20'] > h4_last['ema_50'] > h4_last['ema_200']
    h4_down = h4_last['ema_20'] < h4_last['ema_50'] < h4_last['ema_200']

    # H1 MACD
    h1_macd_up = h1['macd_hist'].iloc[-1] > h1['macd_hist'].iloc[-2]
    h1_macd_down = h1['macd_hist'].iloc[-1] < h1['macd_hist'].iloc[-2]

    # M15 candles
    m15_bullish_candle = m15_last['bullish_engulfing'] or m15_last['hammer']
    m15_bearish_candle = m15_last['bearish_engulfing']

    # Scoring logic for BUY
    if d1_uptrend:
        score_buy += 1
    if h4_up:
        score_buy += 1
    if h1_macd_up:
        score_buy += 1
    if m15_bullish_candle:
        score_buy += 1

    # Scoring logic for SELL
    if d1_downtrend:
        score_sell += 1
    if h4_down:
        score_sell += 1
    if h1_macd_down:
        score_sell += 1
    if m15_bearish_candle:
        score_sell += 1

    entry_price = m15_last['close']
    atr = m15_last['atr']

    threshold = 3

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
            "strategy": "trend",
            "timeframe": "M15",
            "direction": "BUY",
            "entry": float(entry_price),
            "stop_loss": float(entry_price - 1.5 * atr),
            "take_profit": float(entry_price + 3 * atr),
            "confidence": confidence,
            "reason": f"Trend strategy confluence BUY score = {score_buy}"
        }
    if score_sell >= threshold:
        confidence = get_confidence(score_sell)
        return {
            "symbol": symbol,
            "strategy": "trend",
            "timeframe": "M15",
            "direction": "SELL",
            "entry": float(entry_price),
            "stop_loss": float(entry_price + 1.5 * atr),
            "take_profit": float(entry_price - 3 * atr),
            "confidence": confidence,
            "reason": f"Trend strategy confluence SELL score = {score_sell}"
        }
    return {}
from app.indicators.ta_engine import add_indicators
from typing import Dict, Any
import pandas as pd

def detect_trend_signal(df: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
    df = add_indicators(df)
    
    # Fill NaN values to prevent comparison errors (fix deprecated method)
    df = df.ffill().fillna(0)
    
    last = df.iloc[-1]

    # Extract values with safe conversion
    price = float(last.get('close', 0))
    ema_20 = float(last.get('ema_20', 0))
    ema_50 = float(last.get('ema_50', 0))
    ema_200 = float(last.get('ema_200', 0))
    
    # Check if we have valid data
    if price == 0 or ema_20 == 0 or ema_50 == 0 or ema_200 == 0:
        return {"signal": "No valid data"}

    # More flexible trend conditions
    strong_trend_up = ema_20 > ema_50 > ema_200
    weak_trend_up = ema_20 > ema_50 and price > ema_50  # Less strict
    strong_trend_down = ema_20 < ema_50 < ema_200
    weak_trend_down = ema_20 < ema_50 and price < ema_50  # Less strict

    # Much more flexible pullback zone
    near_ema20 = abs(price - ema_20) / price < 0.02  # 2% threshold
    near_ema50 = abs(price - ema_50) / price < 0.02  # 2% threshold
    pullback = near_ema20 or near_ema50

    # Momentum - safe MACD check
    macd_rising = False
    macd_falling = False
    macd_positive = False
    macd_negative = False
    
    if len(df) >= 2:
        macd_current = float(df['macd_hist'].iloc[-1]) if pd.notna(df['macd_hist'].iloc[-1]) else 0
        macd_prev = float(df['macd_hist'].iloc[-2]) if pd.notna(df['macd_hist'].iloc[-2]) else 0
        macd_rising = macd_current > macd_prev
        macd_falling = macd_current < macd_prev
        macd_positive = macd_current > 0
        macd_negative = macd_current < 0

    # SuperTrend direction - safe check
    st_direction = last.get('supertrend_direction', 0)
    st_bullish = float(st_direction) == 1 if pd.notna(st_direction) else False
    st_bearish = float(st_direction) == -1 if pd.notna(st_direction) else False

    # Candle confirmation - safe boolean conversion
    bull_candle = bool(last.get('bullish_engulfing', False)) or bool(last.get('hammer', False))
    bear_candle = bool(last.get('bearish_engulfing', False))

    # Calculate stop loss and take profit
    std_dev = float(df['close'].rolling(14).std().iloc[-1]) if pd.notna(df['close'].rolling(14).std().iloc[-1]) else price * 0.01

    # MUCH MORE FLEXIBLE BUY CONDITIONS - only need trend + ONE other confirmation
    if (strong_trend_up or weak_trend_up) and (pullback or macd_rising or macd_positive or st_bullish or bull_candle):
        confidence = 85
        reason = ""
        
        if strong_trend_up:
            reason += "Strong EMA trend up"
            confidence += 5
        elif weak_trend_up:
            reason += "EMA trend up"
            confidence += 2
            
        if pullback: 
            reason += " + pullback"
            confidence += 2
        if macd_rising: 
            reason += " + MACD rising"
            confidence += 2
        if macd_positive:
            reason += " + MACD positive"
            confidence += 1
        if st_bullish: 
            reason += " + SuperTrend bullish"
            confidence += 2
        if bull_candle: 
            reason += " + bullish candle"
            confidence += 2
            
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": "BUY",
            "entry": round(price, 5),
            "stop_loss": round(price - 2 * std_dev, 5),
            "take_profit": round(price + 4 * std_dev, 5),
            "confidence": min(confidence, 95),
            "reason": reason
        }

    # MUCH MORE FLEXIBLE SELL CONDITIONS - only need trend + ONE other confirmation
    if (strong_trend_down or weak_trend_down) and (pullback or macd_falling or macd_negative or st_bearish or bear_candle):
        confidence = 85
        reason = ""
        
        if strong_trend_down:
            reason += "Strong EMA trend down"
            confidence += 5
        elif weak_trend_down:
            reason += "EMA trend down"
            confidence += 2
            
        if pullback: 
            reason += " + pullback"
            confidence += 2
        if macd_falling: 
            reason += " + MACD falling"
            confidence += 2
        if macd_negative:
            reason += " + MACD negative"
            confidence += 1
        if st_bearish: 
            reason += " + SuperTrend bearish"
            confidence += 2
        if bear_candle: 
            reason += " + bearish candle"
            confidence += 2
            
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": "SELL",
            "entry": round(price, 5),
            "stop_loss": round(price + 2 * std_dev, 5),
            "take_profit": round(price - 4 * std_dev, 5),
            "confidence": min(confidence, 95),
            "reason": reason
        }

    return {"signal": "No valid trend signal"}