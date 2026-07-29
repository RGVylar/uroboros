"""Denunciar y bloquear: lo que Play exige y lo que impide volver a entrar."""
import pytest

from conftest import API, auth


@pytest.fixture(autouse=True)
def _silence_alerts(monkeypatch):
    """La denuncia manda un aviso a Telegram; aquí solo se prueba el bloqueo."""
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("app.routers.friends.send_report_alert", _noop)


def _befriend(client, a, b) -> int:
    fid = client.post(f"{API}/friends", json={"email": b.email}, headers=auth(a)).json()["id"]
    client.patch(f"{API}/friends/{fid}", json={"status": "accepted"}, headers=auth(b))
    return fid


def _report(client, who, fid, reason="Foto ofensiva"):
    return client.post(f"{API}/friends/{fid}/report", json={"reason": reason}, headers=auth(who))


# ── El bloqueo aguanta ──────────────────────────────────────────────────────

def test_report_blocks_and_hides_the_relationship(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    fid = _befriend(client, ruben, silva)

    assert _report(client, silva, fid).status_code == 204

    assert client.get(f"{API}/friends", headers=auth(silva)).json() == []
    assert client.get(f"{API}/friends", headers=auth(ruben)).json() == []


def test_blocked_person_cannot_send_a_new_request(client, make_user):
    """El agujero real: la rama de 'rejected' de send_request reabre la solicitud."""
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _report(client, silva, _befriend(client, ruben, silva))

    r = client.post(f"{API}/friends", json={"email": silva.email}, headers=auth(ruben))
    assert r.status_code == 403


def test_blocked_person_cannot_send_a_request_by_code_either(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _report(client, silva, _befriend(client, ruben, silva))

    code = client.get(f"{API}/users/me/invite-code", headers=auth(silva)).json()["code"]
    assert client.post(f"{API}/friends", json={"code": code}, headers=auth(ruben)).status_code == 403


def test_blocked_person_cannot_delete_the_row_to_escape_the_block(client, make_user):
    """Borrar la fila liberaría el hueco del UNIQUE y permitiría volver."""
    ruben, silva = make_user("Ruben"), make_user("Silva")
    fid = _befriend(client, ruben, silva)
    _report(client, silva, fid)

    assert client.delete(f"{API}/friends/{fid}", headers=auth(ruben)).status_code == 403


def test_blocked_person_cannot_revive_it_with_a_patch(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    fid = _befriend(client, ruben, silva)
    _report(client, silva, fid)

    r = client.patch(f"{API}/friends/{fid}", json={"status": "accepted"}, headers=auth(ruben))
    assert r.status_code == 403


def test_the_blocker_can_undo_it(client, make_user):
    """Quien bloqueó sí puede borrar la fila: eso es desbloquear."""
    ruben, silva = make_user("Ruben"), make_user("Silva")
    fid = _befriend(client, ruben, silva)
    _report(client, silva, fid)

    assert client.delete(f"{API}/friends/{fid}", headers=auth(silva)).status_code == 204
    # Y con la fila fuera, volver a empezar es posible.
    assert client.post(f"{API}/friends", json={"email": silva.email}, headers=auth(ruben)).status_code == 201


# ── Lo que el bloqueo tiene que apagar ──────────────────────────────────────

def test_reporting_revokes_every_permission(client, db, make_user):
    from sqlalchemy import select

    from app.models.friendship import Friendship

    ruben, silva = make_user("Ruben"), make_user("Silva")
    fid = _befriend(client, ruben, silva)
    client.patch(f"{API}/friends/{fid}", json={"can_add_food": True}, headers=auth(silva))

    _report(client, silva, fid)

    # La relación ya no sale por ningún listado, así que se mira la fila.
    f = db.scalar(select(Friendship).where(Friendship.id == fid))
    db.refresh(f)
    assert f.can_add_food is False
    assert f.duel_opt_in_requester is False
    assert f.blocked_by == silva.id


def test_reported_user_profile_becomes_unreachable(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _report(client, silva, _befriend(client, ruben, silva))

    assert client.get(f"{API}/users/{silva.id}/profile", headers=auth(ruben)).status_code == 403
