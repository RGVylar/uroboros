"""Ollas: cocinar una vez, comer en varios días, entre los dos.

Lo que queda sale de las entradas del diario, así que apuntar resta y borrar
devuelve. Los gramos solo existen si alguien pesó la olla ya cocinada.
"""
from conftest import API, auth
from test_partner_edit import _partner_can_write

AT = "2026-10-13T14:00:00Z"


def _product(db, name, kcal):
    from app.models import Product
    from app.models.product import ProductSource

    p = Product(name=name, calories_per_100g=kcal, protein_per_100g=10,
                carbs_per_100g=10, fat_per_100g=1, source=ProductSource.manual)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _pot(client, db, owner, servings=4, **extra):
    pasta, salsa = _product(db, "Pasta", 350), _product(db, "Tomate", 80)
    body = {"name": "Macarrones", "servings": servings, "ingredients": [
        {"product_id": pasta.id, "grams": 1000},
        {"product_id": salsa.id, "grams": 500},
    ], **extra}
    r = client.post(f"{API}/pots", json=body, headers=auth(owner))
    assert r.status_code == 201, r.text
    return r.json()


def _log(client, user, pot_id, expect=201, **amount):
    body = {"meal_type": "lunch", "consumed_at": AT, **amount}
    r = client.post(f"{API}/pots/{pot_id}/log", json=body, headers=auth(user))
    assert r.status_code == expect, r.text
    return r.json()


def _entries(client, user):
    r = client.get(f"{API}/diary/day?day=2026-10-13", headers=auth(user))
    assert r.status_code == 200, r.text
    return [e for m in r.json()["meals"] for e in m["entries"]]


def test_create_totals_and_list(client, db, make_user):
    ana = make_user("Ana")
    pot = _pot(client, db, ana)
    assert pot["calories"] == 3500 + 400
    assert pot["raw_weight"] == 1500
    assert pot["remaining"] == 4
    assert pot["cooked_weight"] is None
    assert [p["id"] for p in client.get(f"{API}/pots", headers=auth(ana)).json()] == [pot["id"]]


def test_serving_scales_every_ingredient_and_drains_the_pot(client, db, make_user):
    ana = make_user("Ana")
    pot = _log(client, ana, _pot(client, db, ana)["id"], servings=1)
    assert pot["remaining"] == 3
    entries = _entries(client, ana)
    assert sorted(e["grams"] for e in entries) == [125, 250]
    assert round(sum(e["calories"] for e in entries)) == round(3900 / 4)


def test_grams_need_the_cooked_weight(client, db, make_user):
    ana = make_user("Ana")
    pot = _pot(client, db, ana)
    _log(client, ana, pot["id"], expect=400, grams=250)


def test_grams_are_a_share_of_the_cooked_pot_not_of_raw_pasta(client, db, make_user):
    # 1 kg de pasta seca pesa ~2,3 kg cocida: 250 g del plato son el 10 % de la
    # olla, no 250 g de pasta seca.
    ana = make_user("Ana")
    pot = _pot(client, db, ana, cooked_weight=2500)
    _log(client, ana, pot["id"], grams=250)
    pasta = next(e for e in _entries(client, ana) if e["grams"] > 90)
    assert pasta["grams"] == 100


def test_weighing_later_scales_what_is_left_to_the_whole_pot(client, db, make_user):
    ana = make_user("Ana")
    pot = _pot(client, db, ana)
    _log(client, ana, pot["id"], servings=2)  # queda la mitad
    r = client.patch(f"{API}/pots/{pot['id']}", json={"weight_now": 1200}, headers=auth(ana))
    assert r.status_code == 200, r.text
    assert r.json()["cooked_weight"] == 2400


def test_never_takes_more_than_what_is_left(client, db, make_user):
    ana = make_user("Ana")
    pot = _pot(client, db, ana)
    _log(client, ana, pot["id"], servings=3)
    left = _log(client, ana, pot["id"], servings=2)
    assert left["remaining"] == 0
    _log(client, ana, pot["id"], expect=409, servings=1)
    # Vacía deja de salir en la lista.
    assert client.get(f"{API}/pots", headers=auth(ana)).json() == []


def test_deleting_an_entry_gives_it_back(client, db, make_user):
    ana = make_user("Ana")
    pot = _pot(client, db, ana)
    _log(client, ana, pot["id"], rest=True)
    assert client.get(f"{API}/pots", headers=auth(ana)).json() == []
    for e in _entries(client, ana):
        assert client.delete(f"{API}/diary/{e['id']}", headers=auth(ana)).status_code == 204
    again = client.get(f"{API}/pots", headers=auth(ana)).json()
    assert again[0]["remaining"] == 4


def test_shared_with_partner_both_ways(client, db, make_user):
    ana, bea = make_user("Ana"), make_user("Bea")
    _partner_can_write(client, ana, bea)  # Bea deja que Ana escriba en su diario
    pot = _pot(client, db, ana)
    assert pot["partner_id"] == bea.id

    # Bea la ve y apunta lo suyo.
    assert client.get(f"{API}/pots", headers=auth(bea)).json()[0]["id"] == pot["id"]
    _log(client, bea, pot["id"], servings=1)
    # Ana apunta para las dos: una ración a cada una.
    out = _log(client, ana, pot["id"], servings=1, also_for_user_id=bea.id)
    eaten = {e["user_id"]: e["servings"] for e in out["eaten"]}
    assert eaten == {ana.id: 1, bea.id: 2}
    assert out["remaining"] == 1


def test_both_with_rest_splits_it(client, db, make_user):
    ana, bea = make_user("Ana"), make_user("Bea")
    _partner_can_write(client, ana, bea)
    pot = _pot(client, db, ana, servings=3)
    out = _log(client, ana, pot["id"], rest=True, also_for_user_id=bea.id)
    assert {e["servings"] for e in out["eaten"]} == {1.5}


def test_not_shared_pot_is_private(client, db, make_user):
    ana, bea, eve = make_user("Ana"), make_user("Bea"), make_user("Eve")
    _partner_can_write(client, ana, bea)
    pot = _pot(client, db, ana, shared=False)
    assert pot["partner_id"] is None
    assert client.get(f"{API}/pots", headers=auth(bea)).json() == []
    assert client.get(f"{API}/pots/{pot['id']}", headers=auth(eve)).status_code == 404
    _log(client, ana, pot["id"], expect=403, servings=1, also_for_user_id=bea.id)


def test_finish_hides_it_and_keeps_the_diary(client, db, make_user):
    ana = make_user("Ana")
    pot = _pot(client, db, ana)
    _log(client, ana, pot["id"], servings=1)
    assert client.post(f"{API}/pots/{pot['id']}/finish", headers=auth(ana)).status_code == 200
    assert client.get(f"{API}/pots", headers=auth(ana)).json() == []
    assert len(_entries(client, ana)) == 2
    _log(client, ana, pot["id"], expect=409, servings=1)


def test_from_recipe_copies_ingredients(client, db, make_user):
    ana = make_user("Ana")
    pollo = _product(db, "Pollo", 120)
    r = client.post(f"{API}/recipes", json={"name": "Pollo", "share_scope": "none",
                    "ingredients": [{"product_id": pollo.id, "grams": 800}]}, headers=auth(ana))
    recipe_id = r.json()["id"]
    r = client.post(f"{API}/pots", json={"name": "Pollo del finde", "servings": 4,
                    "recipe_id": recipe_id}, headers=auth(ana))
    assert r.status_code == 201, r.text
    assert r.json()["raw_weight"] == 800
    # Editar la receta después no cambia la olla.
    client.put(f"{API}/recipes/{recipe_id}", json={"name": "Pollo", "share_scope": "none",
               "ingredients": [{"product_id": pollo.id, "grams": 100}]}, headers=auth(ana))
    assert client.get(f"{API}/pots/{r.json()['id']}", headers=auth(ana)).json()["raw_weight"] == 800


def test_deleting_the_owner_keeps_the_partner_diary(client, db, make_user):
    ana, bea = make_user("Ana"), make_user("Bea")
    _partner_can_write(client, ana, bea)
    pot = _pot(client, db, ana)
    _log(client, bea, pot["id"], servings=1)
    assert client.delete(f"{API}/users/me", headers=auth(ana)).status_code == 204
    assert len(_entries(client, bea)) == 2
    assert client.get(f"{API}/pots", headers=auth(bea)).json() == []
