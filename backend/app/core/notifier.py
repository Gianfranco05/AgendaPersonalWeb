import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
COOLDOWN_SECONDS = 300

_last_alerts: dict[str, float] = {}


def _can_send(event_type: str) -> bool:
    now = time.time()
    last = _last_alerts.get(event_type)
    if last and (now - last) < COOLDOWN_SECONDS:
        return False
    _last_alerts[event_type] = now
    return True


async def send_telegram_alert(
    message: str,
    event_type: str = "default",
) -> None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        return

    if not _can_send(event_type):
        logger.debug("Cooldown active for %s, skipping alert", event_type)
        return

    url = TELEGRAM_API_URL.format(token=bot_token)
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        logger.info("Telegram alert sent for %s", event_type)
    except Exception as e:
        logger.warning("Failed to send Telegram alert: %s", e)
