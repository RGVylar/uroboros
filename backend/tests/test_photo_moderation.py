"""Rechazar una foto desde el chat de admin, y quién puede hacerlo."""
from io import BytesIO

import pytest
from PIL import Image

from conftest import API, auth

from app.config import settings
from app.services.avatar_photo_service import media_root

SECRET = "secreto-de-prueba"
CHAT = "12345"


@pytest.fixture(autouse=True)
def _webhook_configured(monkeypatch):
    monkeypatch.setattr(settings, "telegram_webhook_secret", SECRET)
    monkeypatch.setattr(settings, "telegram_chat_id", CHAT)
    # Ni avisos a Telegram ni push reales durante los tests del webhook.
    async def _noop(*a, **k):
        return None

    monkeypatch.setattr("app.routers.telegram.answer_callback", _noop)
    monkeypatch.setattr("app.routers.telegram.strike_caption", _noop)
    monkeypatch.setattr("app.services.photo_moderation._send_to_user", lambda *a, **k: None)


def _jpeg() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (400, 400), (10, 200, 80)).save(buf, "JPEG")
    return buf.getvalue()


def _upload(client, user) -> str:
    r = client.post(
        f"{API}/users/me/avatar-photo",
        files={"file": ("f.jpg", _jpeg(), "image/jpeg")},
        headers=auth(user),
    )
    assert r.status_code == 200, r.text
    return r.json()["avatar_photo"]


def _callback(client, user_id: int, stem: str, secret: str = SECRET, chat: str = CHAT):
    return client.post(
        f"{API}/telegram/webhook",
        json={
            "callback_query": {
                "id": "cb1",
                "data": f"rp:{user_id}:{stem}",
                "message": {"message_id": 99, "chat": {"id": chat}},
            }
        },
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
    )


# ── Lo que protege una ruta pública ─────────────────────────────────────────

def test_wrong_secret_is_rejected(client, make_user):
    ruben = make_user("Ruben")
    photo = _upload(client, ruben)
    r = _callback(client, ruben.id, photo.removesuffix(".webp"), secret="no-es")
    assert r.status_code == 403
    assert (media_root() / photo).exists()


def test_missing_secret_is_rejected(client, make_user):
    ruben = make_user("Ruben")
    photo = _upload(client, ruben)
    r = client.post(f"{API}/telegram/webhook", json={"callback_query": {"id": "x", "data": "rp:1:a"}})
    assert r.status_code == 403
    assert (media_root() / photo).exists()


def test_another_chat_cannot_moderate(client, make_user):
    """Si alguien mete el bot en otro grupo, sus botones no hacen nada."""
    ruben = make_user("Ruben")
    photo = _upload(client, ruben)
    r = _callback(client, ruben.id, photo.removesuffix(".webp"), chat="99999")
    assert r.status_code == 200
    assert (media_root() / photo).exists()


def test_webhook_is_invisible_when_not_configured(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "telegram_webhook_secret", "")
    r = _callback(client, 1, "abc")
    assert r.status_code == 404


# ── El rechazo en sí ────────────────────────────────────────────────────────

def test_rejecting_deletes_the_photo_and_clears_the_row(client, db, make_user):
    ruben = make_user("Ruben")
    photo = _upload(client, ruben)

    assert _callback(client, ruben.id, photo.removesuffix(".webp")).status_code == 200

    db.refresh(ruben)
    assert ruben.avatar_photo is None
    assert not (media_root() / photo).exists()


def test_rejecting_notifies_the_person(client, db, make_user, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.services.photo_moderation._send_to_user",
        lambda db, uid, **kw: sent.append((uid, kw)),
    )
    ruben = make_user("Ruben")
    photo = _upload(client, ruben)

    _callback(client, ruben.id, photo.removesuffix(".webp"))

    assert len(sent) == 1
    uid, kw = sent[0]
    assert uid == ruben.id
    assert "no cumple" in kw["body"]


def test_stale_alert_does_not_delete_the_new_photo(client, db, make_user):
    """Rechazar un aviso viejo no puede llevarse una foto que nadie ha revisado."""
    ruben = make_user("Ruben")
    old = _upload(client, ruben)
    new = _upload(client, ruben)  # la cambió después del aviso

    assert _callback(client, ruben.id, old.removesuffix(".webp")).status_code == 200

    db.refresh(ruben)
    assert ruben.avatar_photo == new
    assert (media_root() / new).exists()


def test_garbage_callback_data_is_ignored(client):
    """Telegram manda de todo por el webhook; lo raro se descarta con un 200."""
    for data in ["", "otra:cosa", "rp:no-es-un-numero:x", "rp:1"]:
        r = client.post(
            f"{API}/telegram/webhook",
            json={"callback_query": {"id": "x", "data": data, "message": {"chat": {"id": CHAT}}}},
            headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
        )
        assert r.status_code == 200, data


def test_non_callback_updates_are_ignored(client):
    r = client.post(
        f"{API}/telegram/webhook",
        json={"message": {"text": "hola"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert r.status_code == 200
