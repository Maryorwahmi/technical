# Forex pairs and timeframes for scheduler jobs

PAIRS = [
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

TIMEFRAMES = [
    "M15", "H1", "H4", "D1"
]
