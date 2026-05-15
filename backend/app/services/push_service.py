"""Push notifications: Web Push (VAPID) + Firebase Cloud Messaging (FCM)."""

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


# ── Firebase Cloud Messaging ──────────────────────────────────────────────────

def _init_firebase() -> bool:
    """Initialize Firebase Admin SDK once from the credentials JSON env var."""
    creds_json = settings.firebase_credentials_json
    if not creds_json:
        return False
    try:
        import firebase_admin
        from firebase_admin import credentials
        try:
            firebase_admin.get_app()
        except ValueError:
            cred = credentials.Certificate(json.loads(creds_json))
            firebase_admin.initialize_app(cred)
        return True
    except Exception as e:
        logger.error("Firebase init failed: %s", e)
        return False


_firebase_ready = _init_firebase()


def send_fcm(
    *,
    token: str,
    title: str,
    body: str,
    url: str = "/",
    icon: str = "/icon-192.png",
) -> bool:
    """Send a push notification via FCM to a single device token. Returns True on success."""
    if not _firebase_ready:
        return False
    try:
        from firebase_admin import messaging
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={"url": url},
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    icon="ic_launcher",
                    color="#00E676",
                    sound="default",
                ),
            ),
            token=token,
        )
        messaging.send(message)
        return True
    except Exception as e:
        # Token invalid/expired — caller should delete it
        if "registration-token-not-registered" in str(e) or "invalid-registration-token" in str(e):
            raise
        logger.error("FCM send failed: %s", e)
        return False
