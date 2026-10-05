"""Diagnóstico de la APK: se reenvía a Telegram con el dispositivo del UA."""
import pytest

from conftest import API, auth

ANDROID_UA = (
    "Mozilla/5.0 (Linux; Android 14; SM-A546B Build/UP1A.231005.007; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36"
)


@pytest.fixture()
def alerts(monkeypatch):
    sent = []

    async def _capture(*args, **kwargs):
        sent.append(args)

    monkeypatch.setattr("app.routers.diagnostics.send_diagnostic_alert", _capture)
    return sent


def _post(client, user, **body):
    payload = {"kind": "health", "outcome": "denied", "app_version": "1.20", "platform": "android", "data": {}}
    payload.update(body)
    return client.post(
        f"{API}/diagnostics", json=payload, headers={**auth(user), "User-Agent": ANDROID_UA}
    )


def test_forwards_with_device(client, make_user, alerts):
    ana = make_user("Ana")
    r = _post(client, ana, outcome="ok", previous="denied", data={"days": 3})
    assert r.status_code == 204, r.text
    (args,) = alerts
    assert args[2:5] == ("health", "ok", "denied")
    assert "SM-A546B" in args[7]
    assert args[8] == {"days": 3}


def test_requires_auth(client):
    r = client.post(f"{API}/diagnostics", json={"kind": "health", "outcome": "ok", "platform": "android"})
    assert r.status_code == 401


def test_rejects_huge_data(client, make_user, alerts):
    ana = make_user("Ana")
    r = _post(client, ana, data={"blob": "x" * 5000})
    assert r.status_code == 413
    assert alerts == []
