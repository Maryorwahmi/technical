from app.strategies.mtf_confluence_with_d1 import detect_mtf_confluence_signal
from app.data.data_utils import fetch_mtf_data
from app.data.mt5_client import place_order, get_account_balance
from app.utils.risk_utils import calculate_lot_size
from app.notifications.telegram_bot import send_signal_to_telegram
from app.database.db_utils import save_signal, save_forecast_signal
import logging

logger = logging.getLogger(__name__)

def run_all_strategies(df, symbol, timeframe):
    """Generate signals using MTF confluence strategy"""
    signals = []
    
    try:
        # For MTF analysis, we ignore the passed df and timeframe
        # and fetch all required timeframes internally
        mtf_data = fetch_mtf_data(symbol)

        # Use your standard MTF confluence logic
        sig = detect_mtf_confluence_signal(mtf_data, symbol)

        if sig:
            logger.info(f"🔍 {symbol}: {sig['direction']} signal - {sig['reason']}")
            
            # ✅ FIX: Only process signals with trading data (BUY/SELL)
            if sig['direction'] in ['BUY', 'SELL']:
                # Signal has entry/SL/TP data - proceed with trading logic
                logger.info(f"🎯 {symbol}: Processing {sig['direction']} signal with {sig['confidence']}% confidence")
                
                balance = get_account_balance()
                sl_pips = abs(sig['entry'] - sig['stop_loss']) * 10000  # adjust for 5-digit pairs
                lot = calculate_lot_size(balance, risk_percent=1.0, sl_pips=sl_pips)

                sig["lot_size"] = lot

                if sig['confidence'] >= 90:
                    logger.info(f"🚀 {symbol}: High confidence (90%+) - Executing trade")
                    send_signal_to_telegram(sig)
                    save_signal(sig)
                    executed = place_order(
                        symbol=sig['symbol'],
                        direction=sig['direction'],
                        entry=sig['entry'],
                        sl=sig['stop_loss'],
                        tp=sig['take_profit'],
                        lot=lot
                    )
                    sig["executed"] = executed
                elif sig['confidence'] >= 75:
                    logger.info(f"✅ {symbol}: Good confidence (75%+) - Executing trade")
                    send_signal_to_telegram(sig)
                    save_signal(sig)
                    executed = place_order(
                        symbol=sig['symbol'],
                        direction=sig['direction'],
                        entry=sig['entry'],
                        sl=sig['stop_loss'],
                        tp=sig['take_profit'],
                        lot=lot
                    )
                    sig["executed"] = executed
                else:
                    logger.info(f"📈 {symbol}: Lower confidence ({sig['confidence']}%) - Saving as forecast")
                    save_forecast_signal(sig)
                    sig["forecasted"] = True

                signals.append(sig)
                
            elif sig['direction'] in ['REJECTED', 'NEUTRAL']:
                # ✅ Handle filtered signals (no trading data)
                logger.info(f"🚫 {symbol}: Signal filtered - {sig['reason']}")
                # Don't save filtered signals to avoid database clutter
                
            else:
                # Unknown signal type
                logger.warning(f"❓ {symbol}: Unknown signal direction: {sig['direction']}")
        else:
            logger.warning(f"⚠️  {symbol}: No signal returned from strategy")
            
    except Exception as e:
        logger.error(f"❌ {symbol}: MTF strategy error - {e}")
        import traceback
        traceback.print_exc()

    return signals
