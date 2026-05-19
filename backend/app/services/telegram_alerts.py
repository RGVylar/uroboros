"""
Sends error alerts to a Telegram chat when unhandled exceptions occur.
Configure via TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.
"""
import traceback
from datetime import datetime, timezone

import httpx

from app.config import settings

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


async def send_alert(title: str, body: str) -> None:
    """Fire-and-forget Telegram alert. Silently ignores send failures."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    text = f"🔴 *[uroboros]* {title}\n\n{body}\n\n🕐 {now}"

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                TELEGRAM_API.format(token=settings.telegram_bot_token),
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                },
            )
    except Exception:
        pass  # Never let alerting break the app


async def send_error_alert(method: str, path: str, exc: Exception) -> None:
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    # Keep last 8 lines of traceback to stay within Telegram's 4096 char limit
    tb_short = "".join(tb_lines[-8:]).strip()

    title = f"Error 500 — {method} {path}"
    body = f"`{type(exc).__name__}: {exc}`\n\n```\n{tb_short}\n```"
    await send_alert(title, body)
