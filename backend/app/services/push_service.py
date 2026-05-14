"""Web Push via VAPID — pywebpush 2.x + py-vapid 1.9.x."""

import base64
import json
import logging
import time
from urllib.parse import urlparse

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid import Vapid
from pywebpush import WebPusher, WebPushException

from app.config import settings

logger = logging.getLogger(__name__)

VAPID_PUBLIC_KEY = settings.vapid_public_key


def _make_vapid() -> Vapid | None:
    """Build a Vapid instance from the raw base64url private key scalar,
    bypassing from_string() which mishandles PEM in py-vapid 1.9.x."""
    key_b64 = settings.vapid_private_key
    if not key_b64:
        return None
    padding = "=" * (4 - len(key_b64) % 4)
    key_bytes = base64.urlsafe_b64decode(key_b64 + padding)
    private_value = int.from_bytes(key_bytes, "big")
    priv_key = ec.derive_private_key(private_value, ec.SECP256R1(), default_backend())
    v = Vapid()
    v._private_key = priv_key
    v._public_key = priv_key.public_key()  # public_key property has no setter
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

    payload = json.dumps({"title": title, "body": body, "url": url, "icon": icon})
    try:
        wp = WebPusher(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}}
        )
        # encode() returns CaseInsensitiveDict; encrypted bytes are in ["body"]
        encoded = wp.encode(payload, content_encoding="aes128gcm")
        encrypted = encoded["body"]

        parsed = urlparse(endpoint)
        audience = f"{parsed.scheme}://{parsed.netloc}"
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Encoding": "aes128gcm",
            "TTL": "86400",
        }
        # sign() returns {"Authorization": "vapid t=...,k=..."}
        headers.update(_vapid.sign({
            "sub": settings.vapid_email,
            "aud": audience,
            "exp": int(time.time()) + 86400,
        }))

        response = requests.post(endpoint, data=encrypted, headers=headers, timeout=30)

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
