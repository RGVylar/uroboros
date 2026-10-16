"""La página /beta: apuntarse una vez, sin datos raros y sin que los bots cuenten."""
import pytest
from sqlalchemy import select

from app.models import BetaSignup


@pytest.fixture()
def alerts(monkeypatch):
    sent = []

    async def _capture(*args, **kwargs):
        sent.append(args)

    monkeypatch.setattr("app.routers.beta.send_beta_signup_alert", _capture)
    return sent


def _rows(db):
    return db.scalars(select(BetaSignup)).all()


def test_page_is_served_in_the_requested_language(client):
    r = client.get("/beta?lang=en")
    assert r.status_code == 200
    assert 'lang="en"' in r.text
    assert "I want to try it" in r.text
    assert "{L_" not in r.text and "{APP}" not in r.text


def test_signup_is_stored_lowercased_and_alerts(client, db, alerts):
    r = client.post("/beta?lang=es", data={"email": "  Ana.Test@Gmail.com ", "name": "Ana"})
    assert r.status_code == 200
    assert "ana.test@gmail.com" in r.text
    assert "apps/testing/com.uroboros.app" in r.text

    [row] = _rows(db)
    assert row.email == "ana.test@gmail.com"
    assert row.name == "Ana"
    assert row.lang == "es"
    assert row.added is False
    assert alerts == [("ana.test@gmail.com", 1)]


def test_signing_up_twice_keeps_one_row_and_one_alert(client, db, alerts):
    client.post("/beta", data={"email": "ana@gmail.com"})
    r = client.post("/beta", data={"email": "ANA@gmail.com"})
    assert r.status_code == 200
    assert len(_rows(db)) == 1
    assert len(alerts) == 1


def test_invalid_email_shows_the_form_again(client, db, alerts):
    r = client.post("/beta", data={"email": "no-es-un-email", "name": "<b>x</b>"})
    assert r.status_code == 422
    assert "no parece válido" in r.text
    # Lo que escribió vuelve al formulario, escapado.
    assert "&lt;b&gt;x&lt;/b&gt;" in r.text
    assert _rows(db) == []
    assert alerts == []


def test_honeypot_looks_fine_but_stores_nothing(client, db, alerts):
    r = client.post("/beta", data={"email": "bot@spam.com", "website": "http://spam"})
    assert r.status_code == 200
    assert _rows(db) == []
    assert alerts == []
