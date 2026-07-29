"""
Sends alerts to a Telegram chat for key app events and errors.
Configure via TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.
"""
import json
import traceback
from datetime import datetime, timezone

import httpx

from app.config import settings

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_PHOTO_API = "https://api.telegram.org/bot{token}/sendPhoto"
TELEGRAM_CALLBACK_API = "https://api.telegram.org/bot{token}/answerCallbackQuery"
TELEGRAM_EDIT_CAPTION_API = "https://api.telegram.org/bot{token}/editMessageCaption"


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


async def send_avatar_photo_alert(
    user_id: int, name: str, email: str, image: bytes | None, photo_name: str = ""
) -> None:
    """Foto de perfil nueva — moderación manual.

    No hay moderación automática y no la va a haber a esta escala: lo que hay es
    que cada foto subida aparece en el chat de admin y la miras. Escala hasta
    unas pocas al día; a partir de ahí hace falta otra cosa.

    Si la miniatura falla se manda igual el aviso en texto: enterarse tarde de
    quién ha subido algo es peor que no ver la imagen.
    """
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return

    caption = (
        f"🖼 *[uroboros]* Foto de perfil nueva\n\n"
        f"*Usuario:* {name} (`#{user_id}`)\n"
        f"*Email:* `{email}`\n\n"
        f"🕐 {_now()}"
    )

    if image is None:
        await _send(caption)
        return

    # Botón para rechazar la foto sin salir del chat. El callback_data tiene un
    # tope de 64 bytes, de ahí las claves cortas: "rp:<user_id>:<uuid>" son ~42.
    # Lleva el nombre del fichero para que rechazar una alerta vieja no borre
    # una foto que el usuario haya cambiado desde entonces.
    keyboard = json.dumps({
        "inline_keyboard": [[
            {
                "text": "🚫 Rechazar foto",
                "callback_data": f"rp:{user_id}:{photo_name.removesuffix('.webp')}",
            }
        ]]
    })

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                TELEGRAM_PHOTO_API.format(token=settings.telegram_bot_token),
                data={
                    "chat_id": settings.telegram_chat_id,
                    "caption": caption,
                    "parse_mode": "Markdown",
                    "reply_markup": keyboard,
                },
                files={"photo": (f"avatar-{user_id}.jpg", image, "image/jpeg")},
            )
    except Exception:
        pass


async def answer_callback(callback_id: str, text: str) -> None:
    """Cierra el «reloj» del botón y enseña un aviso corto en el chat."""
    if not settings.telegram_bot_token:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                TELEGRAM_CALLBACK_API.format(token=settings.telegram_bot_token),
                json={"callback_query_id": callback_id, "text": text},
            )
    except Exception:
        pass


async def strike_caption(message_id: int, caption: str) -> None:
    """Reescribe el pie de la foto ya moderada y le quita el botón.

    Sin esto el botón se queda ahí y no hay forma de saber, semanas después, si
    aquella foto se llegó a revisar.
    """
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                TELEGRAM_EDIT_CAPTION_API.format(token=settings.telegram_bot_token),
                json={
                    "chat_id": settings.telegram_chat_id,
                    "message_id": message_id,
                    "caption": caption,
                    "parse_mode": "Markdown",
                    "reply_markup": {"inline_keyboard": []},
                },
            )
    except Exception:
        pass


async def send_report_alert(
    reporter_id: int,
    reporter_name: str,
    reported_id: int,
    reported_name: str,
    reported_email: str,
    reason: str,
    image: bytes | None,
) -> None:
    """Alguien ha denunciado a otra persona. Esto sí pide mirarlo hoy."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return

    caption = (
        f"🚩 *[uroboros]* Denuncia de usuario\n\n"
        f"*Denuncia:* {reporter_name} (`#{reporter_id}`)\n"
        f"*Denunciado:* {reported_name} (`#{reported_id}`)\n"
        f"*Email:* `{reported_email}`\n"
        f"*Motivo:* {reason or '— sin especificar —'}\n\n"
        f"_Ya están bloqueados entre sí._\n\n"
        f"🕐 {_now()}"
    )

    if image is None:
        await _send(caption)
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                TELEGRAM_PHOTO_API.format(token=settings.telegram_bot_token),
                data={
                    "chat_id": settings.telegram_chat_id,
                    "caption": caption,
                    "parse_mode": "Markdown",
                },
                files={"photo": (f"denuncia-{reported_id}.jpg", image, "image/jpeg")},
            )
    except Exception:
        pass


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
