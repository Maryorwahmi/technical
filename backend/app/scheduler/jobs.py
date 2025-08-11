from apscheduler.schedulers.background import BackgroundScheduler
from app.data.mt5_client import fetch_ohlcv
from app.signals.signal_engine import run_all_strategies
from app.core.constants import PAIRS, TIMEFRAMES
import pandas as pd
from app.core.logger import setup_logger
from app.signals.forecast_engine import check_forecast_entries

logger = setup_logger("Scheduler")

def scan_all():
    """Scan all pairs using MTF confluence strategy - ONE call per symbol"""
    total_signals = 0
    filtered_count = 0
    
    for pair in PAIRS:
        try:
            # Run MTF analysis once per symbol (fetches all 4 timeframes internally)
            signals = run_all_strategies(None, pair, "MTF")

            if signals:
                total_signals += len(signals)
                logger.info(f"✅ {len(signals)} MTF signal(s) generated for {pair}")
                
                # Log signal details
                for signal in signals:
                    logger.info(f"   └── {pair}: {signal['direction']} @ {signal.get('confidence', 0)}% - {signal.get('reason', 'No reason')}")
            else:
                filtered_count += 1
                logger.info(f"⚠️  No signals for {pair} - likely filtered by accuracy checks")
                
        except Exception as e:
            logger.error(f"❌ MTF scan error on {pair}: {e}")
            import traceback
            traceback.print_exc()

    # Summary log
    total_pairs = len(PAIRS)
    logger.info(f"📊 SCAN COMPLETE: {total_signals} signals from {total_pairs} pairs, {filtered_count} filtered")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scan_all, 'interval', minutes=30)
    scheduler.add_job(check_forecast_entries, 'interval', minutes=180)  # Check pending entries
    scheduler.start()
    logger.info("Scheduler started: scanning every 30 mins, checking forecast every 180 mins")
