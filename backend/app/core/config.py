from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Forex Analyzer"
    VERSION: str = "0.1.0"
    # Trading pairs organized by category
    PAIRS: list = [
        # High volatility pairs (available on MT5)
        "GBPNZD", "AUDNZD", "EURNZD", "GBPAUD",  
        
        # Major pairs (highest liquidity, available on MT5 and Tiingo)
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
       
        # Commodities (commonly available in MT5 and Tiingo)
        "XAUUSD", "XAGUSD",
        
        # Minor pairs (cross currencies, available on MT5)
        "EURGBP", "EURJPY", "EURCHF", "EURCAD", "EURAUD",
        "GBPJPY", "GBPCHF", "GBPCAD", "GBPAUD",
        "AUDJPY", "CADJPY", "CHFJPY",
        "AUDCAD", "AUDCHF", "CADCHF",
    ]
    
    TIMEFRAMES: list = ["M15", "H1", "H4", "D1"]

    # MetaTrader5 settings (if needed)
    MT5_LOGIN: int = int(os.getenv("MT5_LOGIN", 0))
    MT5_PASSWORD: str = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER: str = os.getenv("MT5_SERVER", "")
    MT5_PATH: str = os.getenv("MT5_PATH", "")

    # Telegram Bot settings
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

settings = Settings()