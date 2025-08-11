from app.indicators.enhanced_ta_engine import add_indicators
from app.strategies.market_filters import MarketConditionFilter
from app.utils.risk_utils import ProfessionalRiskManager
from typing import Dict, Any
import pandas as pd

def detect_mtf_confluence_signal(mtf_data: Dict[str, pd.DataFrame], symbol: str) -> Dict[str, Any]:
    """
    Enhanced MTF confluence with 2 accuracy improvements:
    1. Support/Resistance Levels - Avoid key level failures  
    2. Volatility Filters - Avoid choppy/news spike markets
    """
    # Initialize professional filters
    market_filter = MarketConditionFilter()
    risk_manager = ProfessionalRiskManager()
    
    # Pre-trade professional checks
    if not market_filter.is_trading_session():
        return {
            "symbol": symbol, "timeframe": "M15", "direction": "REJECTED",
            "reason": "Outside major trading session - avoiding low liquidity"
        }
    
    if market_filter.is_news_time():
        return {
            "symbol": symbol, "timeframe": "M15", "direction": "REJECTED", 
            "reason": "High-impact news window - avoiding volatility spike"
        }
    
    spread_ok, spread_msg = market_filter.check_spread_conditions(symbol)
    if not spread_ok:
        return {
            "symbol": symbol, "timeframe": "M15", "direction": "REJECTED",
            "reason": f"Execution conditions: {spread_msg}"
        }
    
    can_trade, risk_msg = risk_manager.can_trade(symbol)
    if not can_trade:
        return {
            "symbol": symbol, "timeframe": "M15", "direction": "REJECTED", 
            "reason": f"Risk management: {risk_msg}"
        }
    
    d1 = add_indicators(mtf_data['D1'])
    h4 = add_indicators(mtf_data['H4'])
    h1 = add_indicators(mtf_data['H1'])
    m15 = add_indicators(mtf_data['M15'])

    d1_last = d1.iloc[-1]
    h4_last = h4.iloc[-1]
    h1_last = h1.iloc[-1]
    m15_last = m15.iloc[-1]

    # 🚫 PRE-FLIGHT ACCURACY CHECKS - Must pass both filters
    
    # 🔥 ACCURACY FILTER 1: Support/Resistance Safety (M15 entry point)
    if not m15_last['safe_entry_zone']:
        return {
            "symbol": symbol,
            "timeframe": "M15", 
            "direction": "REJECTED",
            "reason": f"S/R FILTER: Too close to key levels - avoiding breakout failure (Position: {m15_last['price_position']:.2f})"
        }
    
    # 🔥 ACCURACY FILTER 2: Volatility Check (M15 execution timeframe)
    if not m15_last['volatility_ok']:
        return {
            "symbol": symbol,
            "timeframe": "M15",
            "direction": "REJECTED", 
            "reason": "VOLATILITY FILTER: Unsuitable market conditions - avoiding choppy/spike market"
        }

    # ✅ ALL ACCURACY FILTERS PASSED - Proceed with MTF confluence analysis
    accuracy_bonus = m15_last['accuracy_score']  # 0-2 bonus points (removed volume)

    # 🔧 Enhanced Weighted Scoring System with Accuracy Bonus
    weights = {
        "D1": 2,   # 🧠 Strategic bias (trend filter)
        "H4": 3,   # 💪 Major confluence/confirmation  
        "H1": 2,   # ⚙️ Trigger & momentum check
        "M15": 1   # 🎯 Final candle signal check
    }
    
    max_score = sum(weights.values()) + 2  # = 8 + 2 accuracy bonus = 10 total
    score_buy = 0
    score_sell = 0

    # D1 trend filter - Strategic bias
    d1_uptrend = d1_last['ema_20'] > d1_last['ema_50']
    d1_downtrend = d1_last['ema_20'] < d1_last['ema_50']
    d1_trend_ok = abs(d1_last['ema_20'] - d1_last['ema_50']) / d1_last['close'] > 0.001
    
    # Must have some D1 trend strength to proceed
    if not d1_trend_ok:
        return {
            "symbol": symbol,
            "timeframe": "M15",
            "direction": "NEUTRAL",
            "reason": "No clear D1 trend direction"
        }

    # H4 structure - Major confluence/confirmation
    h4_up = h4_last['ema_20'] > h4_last['ema_50'] > h4_last['ema_200']
    h4_down = h4_last['ema_20'] < h4_last['ema_50'] < h4_last['ema_200']

    # H1 momentum - Trigger & momentum check
    if 'macd_hist' in h1.columns:
        h1_macd_up = h1['macd_hist'].iloc[-1] > h1['macd_hist'].iloc[-2]
        h1_macd_down = h1['macd_hist'].iloc[-1] < h1['macd_hist'].iloc[-2]
    else:
        # Use RSI momentum as fallback
        h1_rsi_rising = h1_last['rsi'] > h1.iloc[-2]['rsi']
        h1_macd_up = h1_rsi_rising and h1_last['rsi'] > 50
        h1_macd_down = not h1_rsi_rising and h1_last['rsi'] < 50

    # M15 candles - Final candle signal check
    m15_bullish_candle = m15_last['bullish_engulfing'] or m15_last['hammer']
    m15_bearish_candle = m15_last['bearish_engulfing']

    # 🎯 Enhanced weighted scoring for BUY with accuracy bonus
    if d1_uptrend:
        score_buy += weights["D1"]
    if h4_up:
        score_buy += weights["H4"]
    if h1_macd_up:
        score_buy += weights["H1"]
    if m15_bullish_candle:
        score_buy += weights["M15"]
    
    # 🔥 Add accuracy bonus to BUY score
    score_buy += accuracy_bonus

    # 🎯 Enhanced weighted scoring for SELL with accuracy bonus
    if d1_downtrend:
        score_sell += weights["D1"]
    if h4_down:
        score_sell += weights["H4"]
    if h1_macd_down:
        score_sell += weights["H1"]
    if m15_bearish_candle:
        score_sell += weights["M15"]
    
    # 🔥 Add accuracy bonus to SELL score
    score_sell += accuracy_bonus

    entry_price = m15_last['close']
    atr = m15_last['atr']

    # 🔧 Enhanced confidence calculation with accuracy scoring
    def get_confidence(score, max_score):
        pct = score / max_score
        if pct >= 0.8:      # 80%+ = 8/10 points
            return 80       # Execute immediately - High accuracy
        elif pct >= 0.7:    # 70%+ = 7/10 points
            return 70       # Execute - Good accuracy
        elif pct >= 0.6:    # 60%+ = 6/10 points
            return 60       # Execute - Acceptable accuracy
        elif pct >= 0.5:    # 50%+ = 5/10 points
            return 50       # Forecast - Lower accuracy
        else:
            return 0        # Skip - Poor accuracy

    # 🔧 Enhanced mutual exclusivity with accuracy consideration
    base_threshold = sum(weights.values()) * 0.5  # 50% of base score = 4/8 points
    accuracy_threshold = base_threshold + 1        # Require at least 1 accuracy point
    
    buy_confidence = get_confidence(score_buy, max_score)
    sell_confidence = get_confidence(score_sell, max_score)
    
    # Enhanced signal generation with accuracy filters passed
    if score_buy >= accuracy_threshold and score_sell < accuracy_threshold:
        # Clear BUY signal with accuracy validation
        if buy_confidence > 0:
            return {
                "symbol": symbol,
                "timeframe": "M15",
                "direction": "BUY",
                "entry": float(entry_price),
                "stop_loss": float(entry_price - 1.5 * atr),
                "take_profit": float(entry_price + 3 * atr),
                "confidence": buy_confidence,
                "reason": f"✅ ENHANCED MTF BUY: {score_buy}/{max_score} ({score_buy/max_score:.1%}) | Accuracy: {accuracy_bonus}/2 | S/R✅ Volatility✅"
            }
            
    elif score_sell >= accuracy_threshold and score_buy < accuracy_threshold:
        # Clear SELL signal with accuracy validation
        if sell_confidence > 0:
            return {
                "symbol": symbol,
                "timeframe": "M15",
                "direction": "SELL",
                "entry": float(entry_price),
                "stop_loss": float(entry_price + 1.5 * atr),
                "take_profit": float(entry_price - 3 * atr),
                "confidence": sell_confidence,
                "reason": f"✅ ENHANCED MTF SELL: {score_sell}/{max_score} ({score_sell/max_score:.1%}) | Accuracy: {accuracy_bonus}/2 | S/R✅ Volatility✅"
            }
            
    elif score_buy >= accuracy_threshold and score_sell >= accuracy_threshold:
        # Conflicting signals - choppy market, skip
        return {
            "symbol": symbol,
            "timeframe": "M15", 
            "direction": "NEUTRAL",
            "reason": f"CONFLICTING: BUY {score_buy}/{max_score} vs SELL {score_sell}/{max_score} - Choppy market despite accuracy filters"
        }
    
    # Below threshold or no signals
    return {
        "symbol": symbol,
        "timeframe": "M15",
        "direction": "NEUTRAL", 
        "reason": f"Below threshold: BUY {score_buy}/{max_score}, SELL {score_sell}/{max_score}"
    }
