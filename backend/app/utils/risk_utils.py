import MetaTrader5 as mt5

def calculate_lot_size(balance, risk_percent, sl_pips, pip_value=10):
    """
    Calculate position size (lot) based on account balance, risk %, and stop loss in pips.
    Args:
        balance (float): Account balance in account currency
        risk_percent (float): Risk per trade as percent of balance
        sl_pips (float): Stop loss distance in pips
        pip_value (float): Value per pip per lot (default: 10 for standard lot)
    Returns:
        float: Lot size rounded to 2 decimals, min 0.01, max 5.0
    """
    risk_amount = balance * (risk_percent / 100)
    lot_size = risk_amount / (sl_pips * pip_value)
    return round(min(max(lot_size, 0.01), 5.0), 2)

class ProfessionalRiskManager:
    def __init__(self):
        self.max_risk_per_trade = 0.02  # 2% max
        self.max_daily_loss = 0.06      # 6% daily max
        self.max_open_trades = 7        # Position limit
        
    def can_trade(self, symbol):
        """Comprehensive trading permission check"""
        # Check daily loss limit
        daily_pnl = self.get_daily_pnl()
        if daily_pnl <= -self.max_daily_loss:
            return False, "Daily loss limit reached"
        
        # Check open positions
        open_positions = len(mt5.positions_get())
        if open_positions >= self.max_open_trades:
            return False, "Maximum positions reached"
        
        # Check symbol-specific risk
        symbol_positions = len(mt5.positions_get(symbol=symbol))
        if symbol_positions >= 2:  # Max 2 per symbol
            return False, f"Maximum positions for {symbol} reached"
        
        return True, "OK"
    
    def calculate_position_size(self, account_balance, sl_pips, symbol):
        """Professional position sizing"""
        # Account for broker margins and leverage
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return 0.01  # Minimum fallback
            
        # Risk-based sizing
        risk_amount = account_balance * self.max_risk_per_trade
        
        # Calculate pip value
        if 'JPY' in symbol:
            pip_value = symbol_info.trade_contract_size * 0.01
        else:
            pip_value = symbol_info.trade_contract_size * 0.0001
            
        if sl_pips <= 0:
            return 0.01
            
        lot_size = risk_amount / (sl_pips * pip_value)
        
        # Apply broker constraints
        lot_size = max(symbol_info.volume_min, lot_size)
        lot_size = min(symbol_info.volume_max, lot_size)
        
        # Round to step size
        step = symbol_info.volume_step
        lot_size = round(lot_size / step) * step
        
        return lot_size
