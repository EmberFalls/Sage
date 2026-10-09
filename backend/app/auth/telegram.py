import json
import logging
import urllib.request
from typing import Optional

from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger("sage.telegram")


def send_telegram_otp(
    phone: str,
    otp: str,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> bool:
    """Send real OTP message to Telegram chat via Telegram Bot API."""
    token = (bot_token or TELEGRAM_BOT_TOKEN).strip()
    chat = (chat_id or TELEGRAM_CHAT_ID).strip()

    if not token or not chat:
        logger.info("Telegram Bot Token or Chat ID not configured; skipping Telegram notification.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    message = (
        f"🌾 <b>Sage — Farmer Portal OTP</b>\n\n"
        f"📱 <b>Mobile Number:</b> <code>+91 {phone[-10:]}</code>\n"
        f"🔑 <b>Your OTP Code:</b> <code>{otp}</code>\n"
        f"⏱ <b>Expires in:</b> 10 minutes\n\n"
        f"<i>Enter this verification code on Sage to securely log into your crop loan portal.</i>"
    )

    payload = {
        "chat_id": chat,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                logger.info(f"Successfully dispatched OTP via Telegram to chat {chat}")
                return True
    except Exception as exc:
        logger.warning(f"Failed to send Telegram OTP message: {exc}")
        return False

    return False
