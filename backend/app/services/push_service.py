"""Web Push via VAPID — wraps pywebpush internals directly to avoid from_string issues."""

import base64
import json
import logging
import time
from urllib.parse import urlparse

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid import Vapid
from pywebpush import WebPusher, WebPushException

from app.config import settings

logger = logging.getLogger(__name__)

VAPID_PUBLIC_KEY = settings.vapid_public_key


def _make_vapid() -> Vapid | None:
    """Build a Vapid instance directly from the raw base64url private key scalar,
    bypassing py_vapid's from_string() which has format compatibility issues."""
    key_b64 = settings.vapid_private_key
    if not key_b64:
        return None
    padding = "=" * (4 - len(key_b64) % 4)
    key_bytes = base64.urlsafe_b64decode(key_b64 + padding)
    private_value = int.from_bytes(key_bytes, "big")
    priv_key = ec.derive_private_key(private_value, ec.SECP256R1(), default_backend())
    v = Vapid()
    v._private_key = priv_key
    v._public_key = priv_key.public_key()  # public_key property reads _public_key, no setter exists
    return v


_vapid: Vapid | None = _make_vapid()


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
    if not _vapid:
        logger.warning("VAPID_PRIVATE_KEY not configured — skipping push")
        return False

    data = json.dumps({"title": title, "body": body, "url": url, "icon": icon})
    try:
        wp = WebPusher(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}}
        )
        # encode() returns the transport headers (CaseInsensitiveDict) and stores
        # the encrypted body in wp.encoded
        headers = wp.encode(data, content_encoding="aes128gcm")

        # sign() expects a claims dict and returns {"Authorization": "vapid t=...,k=..."}
        parsed = urlparse(endpoint)
        audience = f"{parsed.scheme}://{parsed.netloc}"
        vapid_headers = _vapid.sign({
            "sub": settings.vapid_email,
            "aud": audience,
            "exp": int(time.time()) + 86400,
        })
        headers.update(vapid_headers)

        response = wp.send(wp.encoded, headers=headers, ttl=86400)

        if response.status_code == 410:
            raise WebPushException("Gone", response=response)
        if not response.ok:
            logger.error("Push failed %s — %s", response.status_code, response.text[:300])
            return False
        return True

    except WebPushException as e:
        if e.response is not None and e.response.status_code == 410:
            raise
        body_text = e.response.text[:300] if e.response is not None else "no response"
        logger.error("Push failed: %s — %s", e, body_text)
        return False


def vapid_public_key() -> str:
    return VAPID_PUBLIC_KEY
