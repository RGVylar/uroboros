"""Webhook de Telegram: los botones de las alertas de moderación.

Esta ruta es **pública** — la llama Telegram, no un usuario con sesión. Lo que
la protege son dos cosas, y las dos tienen que cumplirse:

1. La cabecera `X-Telegram-Bot-Api-Secret-Token`, que Telegram devuelve tal cual
   se registró en setWebhook. Sin `TELEGRAM_WEBHOOK_SECRET` configurado la ruta
   responde 404, así que en local no existe.
2. Que el chat que pulsa el botón sea el chat de admin configurado. Si alguien
   añade el bot a otro grupo, sus botones no hacen nada.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.photo_moderation import reject_photo
from app.services.telegram_alerts import answer_callback, strike_caption

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook", include_in_schema=False)
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if not settings.telegram_webhook_secret:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    update = await request.json()
    callback = update.get("callback_query")
    if not callback:
        # Telegram manda de todo por aquí (mensajes sueltos, comandos). Lo que
        # no reconocemos se ignora con un 200: un error haría que reintentara.
        return {"ok": True}

    chat_id = str(callback.get("message", {}).get("chat", {}).get("id", ""))
    if chat_id != str(settings.telegram_chat_id):
        return {"ok": True}

    data = callback.get("data", "")
    if not data.startswith("rp:"):
        return {"ok": True}

    try:
        _, raw_user_id, stem = data.split(":", 2)
        user_id = int(raw_user_id)
    except ValueError:
        return {"ok": True}

    result = reject_photo(db, user_id, f"{stem}.webp")
    await answer_callback(callback["id"], result.message)

    if result.ok:
        message_id = callback.get("message", {}).get("message_id")
        if message_id:
            await strike_caption(
                message_id,
                f"🚫 *[uroboros]* Foto rechazada\n\n"
                f"*Usuario:* {result.user_name} (`#{user_id}`)\n"
                f"_Retirada y avisada por notificación._",
            )

    return {"ok": True}
