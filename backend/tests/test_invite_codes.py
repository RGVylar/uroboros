"""Añadir amigos por código: lo que sustituye a dar tu email."""
from conftest import API, auth

from app.invite_codes import format_code, normalize


def _code_of(client, user) -> str:
    r = client.get(f"{API}/users/me/invite-code", headers=auth(user))
    assert r.status_code == 200, r.text
    return r.json()["code"]


# ── El código en sí ─────────────────────────────────────────────────────────

def test_code_is_generated_once_and_reused(client, make_user):
    ruben = make_user("Ruben")
    first = _code_of(client, ruben)
    assert len(first) == 8
    # Pedirlo otra vez no lo cambia: la gente lo comparte, no puede bailar.
    assert _code_of(client, ruben) == first


def test_codes_differ_between_users(client, make_user):
    assert _code_of(client, make_user("Ruben")) != _code_of(client, make_user("Silva"))


def test_rotate_changes_the_code(client, make_user):
    ruben = make_user("Ruben")
    before = _code_of(client, ruben)
    r = client.post(f"{API}/users/me/invite-code/rotate", headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["code"] != before


def test_normalize_forgives_how_people_type_it():
    # Minúsculas, el guion del formato bonito, y la O que en realidad es un cero.
    assert normalize("abcd-2345") == "ABCD2345"
    assert normalize("O1LU2345") == "011V2345"
    # Lo que no es un código no lo es: ni corto, ni con símbolos de fuera.
    assert normalize("ABC") == ""
    assert normalize("ABCD234!") == ""


def test_format_is_two_groups_of_four():
    assert format_code("ABCD2345") == "ABCD-2345"


# ── Usarlo para pedir amistad ───────────────────────────────────────────────

def test_request_by_code_reaches_the_right_person(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    code = _code_of(client, silva)

    r = client.post(f"{API}/friends", json={"code": code, "kind": "friend"}, headers=auth(ruben))
    assert r.status_code == 201, r.text
    assert r.json()["receiver"]["id"] == silva.id


def test_code_is_accepted_however_it_is_typed(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    code = _code_of(client, silva)

    typed = format_code(code).lower()  # tal cual se lo enseñamos, en minúsculas
    r = client.post(f"{API}/friends", json={"code": typed}, headers=auth(ruben))
    assert r.status_code == 201, r.text


def test_unknown_code_is_a_404(client, make_user):
    r = client.post(f"{API}/friends", json={"code": "ZZZZ9999"}, headers=auth(make_user("Ruben")))
    assert r.status_code == 404


def test_malformed_code_does_not_leak_that_it_is_malformed(client, make_user):
    """Un código mal escrito responde igual que uno que no existe.

    Si distinguiésemos, el endpoint iría confirmando qué códigos están cogidos.
    """
    r = client.post(f"{API}/friends", json={"code": "no-es-un-codigo"}, headers=auth(make_user("Ruben")))
    assert r.status_code == 404


def test_email_still_works_for_old_clients(client, make_user):
    """Los APK ya instalados solo saben mandar email; no se les puede romper."""
    ruben, silva = make_user("Ruben"), make_user("Silva")
    r = client.post(f"{API}/friends", json={"email": silva.email}, headers=auth(ruben))
    assert r.status_code == 201, r.text


def test_request_needs_exactly_one_of_code_or_email(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    assert client.post(f"{API}/friends", json={}, headers=auth(ruben)).status_code == 422
    both = {"email": silva.email, "code": _code_of(client, silva)}
    assert client.post(f"{API}/friends", json=both, headers=auth(ruben)).status_code == 422
