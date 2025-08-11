import requests
from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger("Telegram")

def format_signal_message(signal: dict) -> str:
    msg = f"""📈 *{signal['direction']} Signal* – `{signal['symbol']}` ({signal['timeframe']})
*Entry:* `{signal['entry']}`
*SL:* `{signal['stop_loss']}`
*TP:* `{signal['take_profit']}`
*Confidence:* `{signal.get('confidence', 0)}%`
*Reason:* {signal['reason']}"""
    return msg

def send_signal_to_telegram(signal: dict):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    message = format_signal_message(signal)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            logger.info("Telegram alert sent.")
        else:
            logger.error(f"Failed to send Telegram alert: {response.text}")
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
