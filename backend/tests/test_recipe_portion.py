"""Registrar una ración de receta en gramos, no siempre la receta entera.

"200 g de pollo con 100 g de arroz" pesa 300 g en crudo; si el plato hecho
pesa 250 g y me como 125 g, quiero la mitad de cada ingrediente en el diario.
"""
from conftest import API, auth
from test_friendships import _befriend


def _product(db, name, kcal):
    from app.models import Product
    from app.models.product import ProductSource

    p = Product(name=name, calories_per_100g=kcal, protein_per_100g=10,
                carbs_per_100g=10, fat_per_100g=10, source=ProductSource.manual)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _recipe(client, owner, ingredients, total_weight=None):
    body = {"name": "Pollo con arroz", "share_scope": "none", "ingredients": ingredients}
    if total_weight is not None:
        body["total_weight"] = total_weight
    r = client.post(f"{API}/recipes", json=body, headers=auth(owner))
    assert r.status_code == 201, r.text
    return r.json()


def _log(client, user, recipe_id, grams=None, **extra):
    body = {"recipe_id": recipe_id, "meal_type": "lunch",
            "consumed_at": "2026-09-14T14:00:00Z", **extra}
    if grams is not None:
        body["grams"] = grams
    r = client.post(f"{API}/diary/recipe", json=body, headers=auth(user))
    assert r.status_code == 201, r.text
    return r.json()


def test_weight_defaults_to_sum_of_ingredients(client, db, make_user):
    ruben = make_user("Ruben")
    pollo, arroz = _product(db, "Pollo", 120), _product(db, "Arroz", 350)
    recipe = _recipe(client, ruben, [
        {"product_id": pollo.id, "grams": 200},
        {"product_id": arroz.id, "grams": 100},
    ])
    assert recipe["total_weight"] is None
    assert recipe["weight"] == 300


def test_final_weight_overrides_the_sum(client, db, make_user):
    ruben = make_user("Ruben")
    pollo = _product(db, "Pollo", 120)
    recipe = _recipe(client, ruben, [{"product_id": pollo.id, "grams": 200}], total_weight=150)
    assert recipe["weight"] == 150

    r = client.get(f"{API}/recipes", headers=auth(ruben))
    assert r.json()[0]["weight"] == 150


def test_logging_without_grams_is_the_whole_recipe(client, db, make_user):
    ruben = make_user("Ruben")
    pollo, arroz = _product(db, "Pollo", 120), _product(db, "Arroz", 350)
    recipe = _recipe(client, ruben, [
        {"product_id": pollo.id, "grams": 200},
        {"product_id": arroz.id, "grams": 100},
    ])
    entries = _log(client, ruben, recipe["id"])
    assert sorted(e["grams"] for e in entries) == [100, 200]
    assert sum(e["calories"] for e in entries) == 120 * 2 + 350


def test_logging_a_portion_scales_every_ingredient(client, db, make_user):
    """125 g de un plato de 250 g = la mitad de cada ingrediente."""
    ruben = make_user("Ruben")
    pollo, arroz = _product(db, "Pollo", 120), _product(db, "Arroz", 350)
    recipe = _recipe(client, ruben, [
        {"product_id": pollo.id, "grams": 200},
        {"product_id": arroz.id, "grams": 100},
    ], total_weight=250)

    entries = _log(client, ruben, recipe["id"], grams=125)
    by_product = {e["product_id"]: e for e in entries}
    assert by_product[pollo.id]["grams"] == 100
    assert by_product[arroz.id]["grams"] == 50
    assert by_product[pollo.id]["calories"] == 120
    assert by_product[arroz.id]["calories"] == 175
    # Las entradas siguen etiquetadas con la receta (cuenta para "frecuentes").
    from app.models import DiaryEntry
    assert {e.recipe_id for e in db.query(DiaryEntry)} == {recipe["id"]}


def test_portion_uses_raw_sum_when_no_final_weight(client, db, make_user):
    ruben = make_user("Ruben")
    pollo = _product(db, "Pollo", 120)
    recipe = _recipe(client, ruben, [{"product_id": pollo.id, "grams": 200}])
    entries = _log(client, ruben, recipe["id"], grams=100)
    assert entries[0]["grams"] == 100
    assert entries[0]["calories"] == 120


def test_editing_can_set_and_clear_the_final_weight(client, db, make_user):
    ruben = make_user("Ruben")
    pollo = _product(db, "Pollo", 120)
    recipe = _recipe(client, ruben, [{"product_id": pollo.id, "grams": 200}])
    body = {"name": "Pollo", "share_scope": "none",
            "ingredients": [{"product_id": pollo.id, "grams": 200}], "total_weight": 180}
    r = client.put(f"{API}/recipes/{recipe['id']}", json=body, headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["weight"] == 180

    body.pop("total_weight")
    r = client.put(f"{API}/recipes/{recipe['id']}", json=body, headers=auth(ruben))
    assert r.json()["total_weight"] is None
    assert r.json()["weight"] == 200


def test_copy_keeps_the_final_weight(client, db, make_user):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    _befriend(client, ruben, pilar, kind="partner")
    pollo = _product(db, "Pollo", 120)
    r = client.post(f"{API}/recipes", json={
        "name": "Pollo", "share_scope": "partner", "total_weight": 150,
        "ingredients": [{"product_id": pollo.id, "grams": 200}],
    }, headers=auth(ruben))
    rid = r.json()["id"]

    shared = client.get(f"{API}/recipes/shared", headers=auth(pilar)).json()
    assert shared[0]["weight"] == 150

    copy = client.post(f"{API}/recipes/{rid}/copy", headers=auth(pilar))
    assert copy.status_code == 201, copy.text
    assert copy.json()["weight"] == 150


def test_only_for_partner_logs_in_their_diary_not_mine(client, db, make_user):
    """El cliente ya mandaba only_for_user_id y el backend lo ignoraba."""
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    fid = _befriend(client, ruben, pilar, kind="partner")
    client.patch(f"{API}/friends/{fid}", json={"can_add_food": True}, headers=auth(pilar))
    pollo = _product(db, "Pollo", 120)
    recipe = _recipe(client, ruben, [{"product_id": pollo.id, "grams": 200}])

    entries = _log(client, ruben, recipe["id"], grams=100, only_for_user_id=pilar.id)
    assert [e["user_id"] for e in entries] == [pilar.id]
    assert entries[0]["grams"] == 100

    entries = _log(client, ruben, recipe["id"], also_for_user_id=pilar.id)
    assert sorted(e["user_id"] for e in entries) == sorted([ruben.id, pilar.id])


def test_zero_grams_is_rejected(client, db, make_user):
    ruben = make_user("Ruben")
    pollo = _product(db, "Pollo", 120)
    recipe = _recipe(client, ruben, [{"product_id": pollo.id, "grams": 200}])
    r = client.post(f"{API}/diary/recipe", json={
        "recipe_id": recipe["id"], "meal_type": "lunch",
        "consumed_at": "2026-09-14T14:00:00Z", "grams": 0,
    }, headers=auth(ruben))
    assert r.status_code == 422


def test_a_shared_recipe_can_be_logged_by_the_friend(client, db, make_user):
    """Lo que pasó al desplegar: 'Not your recipe' al registrar una de un amigo."""
    ruben, silva, nadie = make_user("Ruben"), make_user("Silva"), make_user("Nadie")
    _befriend(client, ruben, silva)
    pollo = _product(db, "Pollo", 120)
    r = client.post(f"{API}/recipes", json={
        "name": "Pollo", "share_scope": "friends", "total_weight": 200,
        "ingredients": [{"product_id": pollo.id, "grams": 200}],
    }, headers=auth(ruben))
    rid = r.json()["id"]

    entries = _log(client, silva, rid, grams=100)
    assert [e["user_id"] for e in entries] == [silva.id]
    assert entries[0]["grams"] == 100

    r = client.post(f"{API}/diary/recipe", json={
        "recipe_id": rid, "meal_type": "lunch", "consumed_at": "2026-09-14T14:00:00Z",
    }, headers=auth(nadie))
    assert r.status_code == 403
