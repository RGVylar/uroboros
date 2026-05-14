"""Web Push via VAPID — wraps pywebpush."""

import base64
import json
import logging

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pywebpush import WebPushException, webpush

from app.config import settings

logger = logging.getLogger(__name__)

VAPID_PUBLIC_KEY = settings.vapid_public_key
VAPID_EMAIL = settings.vapid_email


def _private_key_pem(key_b64url: str) -> str:
    """Convert base64url raw EC private key scalar to PEM (what pywebpush expects)."""
    padding = "=" * (4 - len(key_b64url) % 4)
    key_bytes = base64.urlsafe_b64decode(key_b64url + padding)
    private_value = int.from_bytes(key_bytes, "big")
    private_key = ec.derive_private_key(private_value, ec.SECP256R1(), default_backend())
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


# Convert once at import time
_VAPID_PRIVATE_PEM: str = _private_key_pem(settings.vapid_private_key) if settings.vapid_private_key else ""


def send_push(
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
    title: str,
    body: str,
    url: str = "/",
    icon: str = "/icon-192.png",
) -> bool:
    """Send a Web Push notification. Returns True on success."""
    if not _VAPID_PRIVATE_PEM:
        logger.warning("VAPID_PRIVATE_KEY not configured — skipping push")
        return False

    try:
        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {"p256dh": p256dh, "auth": auth},
            },
            data=json.dumps({"title": title, "body": body, "url": url, "icon": icon}),
            vapid_private_key=_VAPID_PRIVATE_PEM,
            vapid_claims={"sub": VAPID_EMAIL},
        )
        return True
    except WebPushException as e:
        if e.response is not None and e.response.status_code == 410:
            raise
        body_text = e.response.text if e.response is not None else "no response"
        logger.error("Push failed %s — %s", e, body_text)
        return False


def vapid_public_key() -> str:
    return VAPID_PUBLIC_KEY
