"""Ver el día de la pareja en tu diario + color de identidad.

Cubre: leer el día de la pareja vía GET /diary/day?user_id (permiso household),
que un amigo normal no pueda, copiarte un plato de la pareja a tu diario, y la
validación del color de identidad.
"""
from conftest import API, auth
from test_friendships import _befriend
from test_partner_edit import _partner_can_write, _log, DAY


def _day(client, actor, target=None):
    url = f"{API}/diary/day?day={DAY}"
    if target is not None:
        url += f"&user_id={target.id}"
    return client.get(url, headers=auth(actor))


# ── Leer el día de la pareja ────────────────────────────────────────────────

def test_partner_can_read_partner_day(client, make_user, make_product):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    _partner_can_write(client, ruben, pilar)
    product = make_product("Avena")
    _log(client, pilar, product, grams=60, meal="breakfast")

    r = _day(client, ruben, target=pilar)
    assert r.status_code == 200, r.text
    entries = r.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["product_id"] == product.id


def test_plain_friend_cannot_read_day(client, make_user, make_product):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _befriend(client, ruben, silva)  # amigo, no pareja
    r = _day(client, silva, target=ruben)
    assert r.status_code == 403


def test_partner_without_optin_cannot_read_day(client, make_user):
    """Pareja pero sin can_add_food: sin permiso household, no ve el día."""
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    _befriend(client, ruben, pilar, kind="partner")  # sin dar can_add_food
    r = _day(client, ruben, target=pilar)
    assert r.status_code == 403


def test_own_day_still_works_without_user_id(client, make_user, make_product):
    ruben = make_user("Ruben")
    product = make_product("Pollo")
    _log(client, ruben, product, grams=100, meal="lunch")
    r = _day(client, ruben)
    assert r.status_code == 200, r.text
    assert len(r.json()["entries"]) == 1


# ── Copiar un plato de la pareja a mi diario ────────────────────────────────

def test_copy_partner_meal_to_me(client, make_user, make_product):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    _partner_can_write(client, ruben, pilar)
    product = make_product("Salmon")
    _log(client, pilar, product, grams=180, meal="dinner")

    # Ruben se lo copia a SÍ MISMO (post normal, sin also/only_for)
    r = client.post(
        f"{API}/diary",
        json={"product_id": product.id, "grams": 180, "consumed_at": f"{DAY}T21:00:00Z", "meal_type": "dinner"},
        headers=auth(ruben),
    )
    assert r.status_code == 201, r.text

    # Ruben tiene su copia; el diario de Pilar sigue con una sola entrada (no se tocó)
    assert len(_day(client, ruben).json()["entries"]) == 1
    assert len(_day(client, pilar).json()["entries"]) == 1


# ── Color de identidad ──────────────────────────────────────────────────────

def test_identity_hue_valid_is_saved_and_exposed(client, make_user):
    ruben = make_user("Ruben")
    r = client.patch(f"{API}/users/me/identity-color", json={"identity_hue": 320}, headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["identity_hue"] == 320


def test_identity_hue_invalid_is_rejected(client, make_user):
    ruben = make_user("Ruben")
    r = client.patch(f"{API}/users/me/identity-color", json={"identity_hue": 100}, headers=auth(ruben))
    assert r.status_code == 422


def test_identity_hue_null_clears(client, make_user):
    ruben = make_user("Ruben")
    client.patch(f"{API}/users/me/identity-color", json={"identity_hue": 265}, headers=auth(ruben))
    r = client.patch(f"{API}/users/me/identity-color", json={"identity_hue": None}, headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["identity_hue"] is None


def test_partner_identity_hue_visible_in_users_list(client, make_user):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    _partner_can_write(client, ruben, pilar)
    client.patch(f"{API}/users/me/identity-color", json={"identity_hue": 195}, headers=auth(pilar))

    users = client.get(f"{API}/users", headers=auth(ruben)).json()
    pilar_row = next(u for u in users if u["id"] == pilar.id)
    assert pilar_row["identity_hue"] == 195
