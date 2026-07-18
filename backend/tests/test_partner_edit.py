"""Poner/quitar a la pareja desde el modal de editar.

Cubre: la consulta "¿la pareja ya tiene este producto en esta comida?" (emparejada
por producto + comida + día, no solo por día) y poder editar/borrar la entrada de la
pareja cuando hay permiso de household. Un amigo normal no puede hacer nada de esto.
"""
from conftest import API, auth
from test_friendships import _befriend

DAY = "2026-07-17"


def _partner_can_write(client, requester, receiver):
    """receiver (pareja) deja que requester escriba en su diario."""
    fid = _befriend(client, requester, receiver, kind="partner")
    r = client.patch(f"{API}/friends/{fid}", json={"can_add_food": True}, headers=auth(receiver))
    assert r.status_code == 200, r.text
    return fid


def _log(client, actor, product, grams=100, meal="lunch", only_for=None, also_for=None):
    body = {
        "product_id": product.id,
        "grams": grams,
        "consumed_at": f"{DAY}T12:00:00Z",
        "meal_type": meal,
    }
    if only_for:
        body["only_for_user_id"] = only_for.id
    if also_for:
        body["also_for_user_id"] = also_for.id
    r = client.post(f"{API}/diary", json=body, headers=auth(actor))
    assert r.status_code == 201, r.text
    return r.json()


def _status(client, actor, partner, product, meal="lunch"):
    r = client.get(
        f"{API}/diary/partner-entry?user_id={partner.id}&product_id={product.id}&day={DAY}&meal_type={meal}",
        headers=auth(actor),
    )
    assert r.status_code == 200, r.text
    return r.json()


def _entries(client, user):
    r = client.get(f"{API}/diary/day?day={DAY}", headers=auth(user))
    assert r.status_code == 200, r.text
    return r.json()["entries"]


# ── Consulta de estado ──────────────────────────────────────────────────────

def test_status_empty_when_partner_has_nothing(client, make_user, make_product):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    _partner_can_write(client, ruben, pilar)
    product = make_product()

    s = _status(client, ruben, pilar, product)
    assert s["entry_id"] is None
    assert s["count"] == 0


def test_status_sees_what_partner_logged_herself(client, make_user, make_product):
    """El punto que motivó todo: aunque la pareja se lo pusiera ella sola, lo vemos."""
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    _partner_can_write(client, ruben, pilar)
    product = make_product("Pollo")
    _log(client, pilar, product, grams=150, meal="lunch")

    s = _status(client, ruben, pilar, product, meal="lunch")
    assert s["entry_id"] is not None
    assert s["grams"] == 150
    assert s["count"] == 1


def test_status_is_scoped_by_meal_not_just_day(client, make_user, make_product):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    _partner_can_write(client, ruben, pilar)
    product = make_product("Pollo")
    _log(client, pilar, product, grams=150, meal="dinner")

    assert _status(client, ruben, pilar, product, meal="lunch")["entry_id"] is None
    assert _status(client, ruben, pilar, product, meal="dinner")["entry_id"] is not None


# ── Añadir / editar / quitar la entrada de la pareja ────────────────────────

def test_add_then_edit_then_remove_partner_entry(client, make_user, make_product):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    _partner_can_write(client, ruben, pilar)
    product = make_product("Pollo")

    # Añadir a la pareja (only_for) con sus propios gramos
    _log(client, ruben, product, grams=150, only_for=pilar)
    s = _status(client, ruben, pilar, product)
    assert s["grams"] == 150
    pid = s["entry_id"]

    # Editar los gramos de la pareja
    r = client.patch(f"{API}/diary/{pid}", json={"grams": 200}, headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert _status(client, ruben, pilar, product)["grams"] == 200

    # Quitárselo solo a la pareja
    r = client.delete(f"{API}/diary/{pid}", headers=auth(ruben))
    assert r.status_code == 204, r.text
    assert _entries(client, pilar) == []


def test_delete_for_both_only_removes_matching_meal(client, make_user, make_product):
    """'Borrar a los dos' empareja por comida: no toca el mismo producto en otra comida."""
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    _partner_can_write(client, ruben, pilar)
    product = make_product("Pollo")

    mine = _log(client, ruben, product, grams=100, meal="lunch", also_for=pilar)
    my_lunch_id = mine[0]["id"]
    # La pareja tiene además pollo en la cena por su cuenta
    _log(client, pilar, product, grams=90, meal="dinner")

    r = client.delete(f"{API}/diary/{my_lunch_id}?also_for_user_id={pilar.id}", headers=auth(ruben))
    assert r.status_code == 204, r.text

    pilar_entries = _entries(client, pilar)
    # Se borró su almuerzo, pero su cena sigue intacta
    assert [e["meal_type"] for e in pilar_entries] == ["dinner"]


# ── Un amigo normal no puede ────────────────────────────────────────────────

def test_plain_friend_cannot_query_partner_status(client, make_user, make_product):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _befriend(client, ruben, silva)  # amigo, no pareja
    product = make_product()

    r = client.get(
        f"{API}/diary/partner-entry?user_id={ruben.id}&product_id={product.id}&day={DAY}&meal_type=lunch",
        headers=auth(silva),
    )
    assert r.status_code == 403


def test_plain_friend_cannot_edit_or_delete_my_entry(client, make_user, make_product):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _befriend(client, ruben, silva)  # amigo, no pareja
    product = make_product()
    mine = _log(client, ruben, product)
    my_id = mine[0]["id"]

    assert client.patch(f"{API}/diary/{my_id}", json={"grams": 5}, headers=auth(silva)).status_code == 404
    assert client.delete(f"{API}/diary/{my_id}", headers=auth(silva)).status_code == 404
    # Y mi entrada sigue como estaba
    assert _entries(client, ruben)[0]["grams"] == 100


def test_delete_only_for_partner_keeps_mine(client, make_user, make_product):
    """'Solo para la pareja' borra su copia y conserva la mía."""
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    _partner_can_write(client, ruben, pilar)
    product = make_product("Pollo")

    mine = _log(client, ruben, product, grams=100, meal="lunch", also_for=pilar)
    my_id = mine[0]["id"]
    assert len(_entries(client, ruben)) == 1
    assert len(_entries(client, pilar)) == 1

    r = client.delete(f"{API}/diary/{my_id}?only_for_user_id={pilar.id}", headers=auth(ruben))
    assert r.status_code == 204, r.text
    assert len(_entries(client, ruben)) == 1
    assert _entries(client, pilar) == []
