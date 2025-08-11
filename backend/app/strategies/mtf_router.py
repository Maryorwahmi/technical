from app.strategies.trend import trend_mtf_logic
from app.strategies.swing import swing_mtf_logic
from app.strategies.breakout import breakout_mtf_logic

def run_mtf_strategy(strategy_name, mtf_data, symbol):
    if strategy_name == "trend":
        return trend_mtf_logic(mtf_data, symbol)
    elif strategy_name == "swing":
        return swing_mtf_logic(mtf_data, symbol)
    elif strategy_name == "breakout":
        return breakout_mtf_logic(mtf_data, symbol)
    return {}
