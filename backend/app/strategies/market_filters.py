import datetime
import MetaTrader5 as mt5

class MarketConditionFilter:
    def __init__(self):
        # Default spread limits for all PAIRS from constants.py
        self.spread_limits = {
            'EURUSD': 2.0, 'GBPUSD': 3.0, 'USDJPY': 2.5,
            'USDCHF': 3.0, 'AUDUSD': 3.5, 'NZDUSD': 4.0,
            'XAUUSD': 5.0, 'XAGUSD': 8.0,
            'GBPNZD': 7.0, 'AUDNZD': 6.0, 'EURNZD': 6.0, 'GBPAUD': 5.0,
            'EURGBP': 2.5, 'EURJPY': 3.0, 'EURCHF': 3.0, 'EURCAD': 4.0, 'EURAUD': 4.0,
            'GBPJPY': 4.0, 'GBPCHF': 4.0, 'GBPCAD': 5.0, 'GBPAUD': 5.0,
            'AUDJPY': 3.5, 'CADJPY': 3.5, 'CHFJPY': 3.5,
            'AUDCAD': 4.0, 'AUDCHF': 4.0, 'CADCHF': 4.0,
        }
    
    def is_trading_session(self):
        """Check if in major trading session"""
        utc_now = datetime.datetime.utcnow()
        hour = utc_now.hour
        
        # Major sessions (UTC)
        london = 8 <= hour <= 17
        ny = 13 <= hour <= 22
        tokyo = 23 <= hour <= 8
        
        # Best overlap times
        london_ny = 13 <= hour <= 17
        tokyo_london = 8 <= hour <= 9
        
        # Avoid low liquidity
        weekend_gap = (hour <= 1 or hour >= 22) and utc_now.weekday() in [4, 6]  # Fri night, Sun
        
        return (london or ny or tokyo) and not weekend_gap
    
    def check_spread_conditions(self, symbol):
        """Validate execution conditions"""
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return False, "No market data"
        
        spread = (tick.ask - tick.bid) * 10000  # Convert to pips
        max_spread = self.spread_limits.get(symbol, 5.0)
        
        if spread > max_spread:
            return False, f"Spread too wide: {spread:.1f} > {max_spread}"
        
        # Check market hours for symbol
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
            return False, "Market closed or restricted"
        
        return True, "OK"
    
    def is_news_time(self):
        """Avoid high-impact news times"""
        utc_now = datetime.datetime.utcnow()
        
        # Major news times (UTC) - expand this with economic calendar
        risky_times = [
            (8, 30, 9, 30),    # London open + data
            (12, 30, 13, 30),  # ECB/UK data
            (14, 30, 15, 30),  # US session open
            (18, 0, 18, 30),   # US data releases
            (20, 0, 20, 30)    # Fed speeches
        ]
        
        current_time = utc_now.hour * 100 + utc_now.minute
        
        for start_h, start_m, end_h, end_m in risky_times:
            start_time = start_h * 100 + start_m  
            end_time = end_h * 100 + end_m
            if start_time <= current_time <= end_time:
                return True
                
        return False