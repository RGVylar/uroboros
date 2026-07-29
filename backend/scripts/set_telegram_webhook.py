#!/usr/bin/env python
"""Registra (o borra) el webhook de Telegram. Se ejecuta una vez, a mano.

    cd /opt/uroboros/backend && .venv/bin/python scripts/set_telegram_webhook.py
    .venv/bin/python scripts/set_telegram_webhook.py --delete

Lee TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET y APP_URL del .env. Sin webhook
registrado las alertas siguen llegando igual: lo único que no funciona es el
botón de rechazar foto.

No se hace al arrancar el backend a propósito. En desarrollo apuntaría el bot a
una URL que no existe y dejaría de funcionar en producción sin que nadie se
entere hasta que hiciera falta.
"""
import sys

import httpx

from app.config import settings


def main() -> int:
    if not settings.telegram_bot_token:
        print("✖ Falta TELEGRAM_BOT_TOKEN en el .env")
        return 1

    base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    if "--delete" in sys.argv:
        r = httpx.post(f"{base}/deleteWebhook", timeout=10)
        print(f"deleteWebhook → {r.status_code} {r.text}")
        return 0 if r.status_code == 200 else 1

    if not settings.telegram_webhook_secret:
        print("✖ Falta TELEGRAM_WEBHOOK_SECRET en el .env")
        print('  Genéralo con: python -c "import secrets; print(secrets.token_urlsafe(32))"')
        return 1

    url = f"{settings.app_url}/api/telegram/webhook"
    r = httpx.post(
        f"{base}/setWebhook",
        json={
            "url": url,
            "secret_token": settings.telegram_webhook_secret,
            # Solo nos interesan los botones. Sin esto Telegram manda además
            # cada mensaje del chat, que no hacemos más que descartar.
            "allowed_updates": ["callback_query"],
        },
        timeout=10,
    )
    print(f"setWebhook {url} → {r.status_code} {r.text}")
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
