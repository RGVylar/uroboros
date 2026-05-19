"""
Sends alerts to a Telegram chat for key app events and errors.
Configure via TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.
"""
import traceback
from datetime import datetime, timezone

import httpx

from app.config import settings

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


async def _send(text: str) -> None:
    """Fire-and-forget. Silently ignores send failures."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
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
        pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


async def send_alert(title: str, body: str) -> None:
    text = f"🔴 *[uroboros]* {title}\n\n{body}\n\n🕐 {_now()}"
    await _send(text)


async def send_error_alert(method: str, path: str, exc: Exception) -> None:
    """500 — unhandled server exception."""
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_short = "".join(tb_lines[-8:]).strip()
    text = (
        f"🔴 *[uroboros]* Error 500 — `{method} {path}`\n\n"
        f"`{type(exc).__name__}: {exc}`\n\n"
        f"```\n{tb_short}\n```\n\n"
        f"🕐 {_now()}"
    )
    await _send(text)


async def send_new_user_alert(name: str, email: str, user_count: int) -> None:
    """New user registered."""
    text = (
        f"👤 *[uroboros]* Nuevo usuario\n\n"
        f"*Nombre:* {name}\n"
        f"*Email:* `{email}`\n"
        f"*Total usuarios:* {user_count}\n\n"
        f"🕐 {_now()}"
    )
    await _send(text)


async def send_brute_force_alert(ip: str, endpoint: str) -> None:
    """Rate limit exceeded on an auth endpoint."""
    text = (
        f"🚨 *[uroboros]* Brute force detectado\n\n"
        f"*IP:* `{ip}`\n"
        f"*Endpoint:* `{endpoint}`\n"
        f"*Acción:* bloqueado con 429\n\n"
        f"🕐 {_now()}"
    )
    await _send(text)


async def send_unusual_4xx_alert(method: str, path: str, status: int, detail: str = "") -> None:
    """Unexpected 4xx on auth endpoints (e.g. malformed requests)."""
    text = (
        f"⚠️ *[uroboros]* Error {status} inusual\n\n"
        f"`{method} {path}`\n"
        f"{detail}\n\n"
        f"🕐 {_now()}"
    )
    await _send(text)
