"""Reportar un problema: que llegue siempre con la versión que lleva el cliente."""
from io import BytesIO

import pytest
from PIL import Image

from app.models import BugReport
from app.services.telegram_alerts import _md_escape
from conftest import API, auth

ANDROID_UA = (
    "Mozilla/5.0 (Linux; Android 14; 23028RA60L Build/UKQ1.230804.001; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36"
)


@pytest.fixture()
def alerts(monkeypatch):
    """Lo que se habría mandado a Telegram, en vez de mandarlo."""
    sent = []

    async def _capture(*args, **kwargs):
        sent.append(args)

    monkeypatch.setattr("app.routers.feedback.send_bug_report_alert", _capture)
    return sent


def _form(**overrides):
    data = {
        "message": "No me sale el botón de pareja",
        "app_version": "1.17",
        "platform": "android",
        "locale": "es",
        "route": "/friends",
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not None}


def _png() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (40, 80), "teal").save(buf, "PNG")
    return buf.getvalue()


def test_report_is_stored_with_version_and_device(client, db, make_user, alerts):
    ruben = make_user("Ruben")
    r = client.post(
        f"{API}/feedback",
        data=_form(),
        headers={**auth(ruben), "User-Agent": ANDROID_UA},
    )
    assert r.status_code == 201, r.text

    report = db.get(BugReport, r.json()["id"])
    assert report.user_id == ruben.id
    assert report.app_version == "1.17"
    assert report.platform == "android"
    assert report.route == "/friends"
    assert report.device.startswith("Linux; Android 14; 23028RA60L")
    assert report.had_screenshot is False

    (args,) = alerts
    assert args[4] == "1.17"  # la versión llega también al aviso
    assert args[-1] is None


def test_report_without_version_is_rejected(client, make_user, alerts):
    """Un informe sin versión es el que costó una tarde: no se acepta."""
    r = client.post(f"{API}/feedback", data=_form(app_version=None), headers=auth(make_user("Ruben")))
    assert r.status_code == 422
    assert alerts == []


def test_blank_message_is_rejected(client, make_user, alerts):
    r = client.post(f"{API}/feedback", data=_form(message="   "), headers=auth(make_user("Ruben")))
    assert r.status_code == 422


def test_unknown_platform_is_rejected(client, make_user, alerts):
    r = client.post(f"{API}/feedback", data=_form(platform="symbian"), headers=auth(make_user("Ruben")))
    assert r.status_code == 422


def test_screenshot_is_reencoded_as_jpeg_and_not_stored(client, db, make_user, alerts):
    r = client.post(
        f"{API}/feedback",
        data=_form(),
        files={"screenshot": ("captura.png", _png(), "image/png")},
        headers=auth(make_user("Ruben")),
    )
    assert r.status_code == 201, r.text
    assert db.get(BugReport, r.json()["id"]).had_screenshot is True

    image = alerts[0][-1]
    assert image[:3] == b"\xff\xd8\xff"  # JPEG, no el PNG que se subió


def test_a_file_that_is_not_an_image_is_rejected(client, make_user, alerts):
    r = client.post(
        f"{API}/feedback",
        data=_form(),
        files={"screenshot": ("captura.png", b"esto no es una imagen", "image/png")},
        headers=auth(make_user("Ruben")),
    )
    assert r.status_code == 422
    assert alerts == []


def test_requires_login(client):
    assert client.post(f"{API}/feedback", data=_form()).status_code == 401


def test_markdown_in_the_message_cannot_break_the_alert():
    assert _md_escape("mi_receta *favorita* `x` [y]") == r"mi\_receta \*favorita\* \`x\` \[y]"
