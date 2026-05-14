"""Web Push via VAPID — wraps pywebpush."""

import json
import logging

from pywebpush import webpush, WebPushException

from app.config import settings

logger = logging.getLogger(__name__)

VAPID_PRIVATE_KEY = settings.vapid_private_key
VAPID_PUBLIC_KEY = settings.vapid_public_key
VAPID_EMAIL = settings.vapid_email


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
    if not VAPID_PRIVATE_KEY:
        logger.warning("VAPID_PRIVATE_KEY not configured — skipping push")
        return False

    try:
        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {"p256dh": p256dh, "auth": auth},
            },
            data=json.dumps({"title": title, "body": body, "url": url, "icon": icon}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_EMAIL},
        )
        return True
    except WebPushException as e:
        # 410 Gone = subscription expired/revoked → caller should delete it
        if e.response is not None and e.response.status_code == 410:
            raise
        logger.error("Push failed: %s", e)
        return False


def vapid_public_key() -> str:
    return VAPID_PUBLIC_KEY
