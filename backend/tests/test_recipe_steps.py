"""Ficha de cocina de una receta: pasos, raciones y tiempos.

Viaja con la receta: se guarda, se edita, la ve quien la tiene compartida y se
lleva en la copia.
"""
from conftest import API, auth
from test_friendships import _befriend
from test_recipe_portion import _product


def _create(client, owner, product_id, **card):
    body = {"name": "Lentejas", "share_scope": "friends",
            "ingredients": [{"product_id": product_id, "grams": 200}], **card}
    r = client.post(f"{API}/recipes", json=body, headers=auth(owner))
    assert r.status_code == 201, r.text
    return r.json()


def test_recipe_without_card_has_no_steps(client, db, make_user):
    ruben = make_user("Ruben")
    p = _product(db, "Lenteja", 350)
    recipe = _create(client, ruben, p.id)
    assert recipe["steps"] == []
    assert recipe["servings"] is None
    assert recipe["prep_minutes"] is None and recipe["cook_minutes"] is None


def test_steps_are_trimmed_and_blanks_dropped(client, db, make_user):
    ruben = make_user("Ruben")
    p = _product(db, "Lenteja", 350)
    recipe = _create(client, ruben, p.id,
                     steps=["  Remojar 8 h ", "", "   ", "Cocer 40 min"],
                     servings=4, prep_minutes=10, cook_minutes=40)
    assert recipe["steps"] == ["Remojar 8 h", "Cocer 40 min"]
    assert (recipe["servings"], recipe["prep_minutes"], recipe["cook_minutes"]) == (4, 10, 40)


def test_update_replaces_the_card(client, db, make_user):
    ruben = make_user("Ruben")
    p = _product(db, "Lenteja", 350)
    recipe = _create(client, ruben, p.id, steps=["Uno"], servings=2)
    r = client.put(f"{API}/recipes/{recipe['id']}", headers=auth(ruben), json={
        "name": "Lentejas", "share_scope": "friends",
        "ingredients": [{"product_id": p.id, "grams": 200}],
        "steps": ["Uno", "Dos"], "servings": None, "cook_minutes": 30,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["steps"] == ["Uno", "Dos"]
    assert body["servings"] is None
    assert body["cook_minutes"] == 30


def test_invalid_servings_rejected(client, db, make_user):
    ruben = make_user("Ruben")
    p = _product(db, "Lenteja", 350)
    r = client.post(f"{API}/recipes", headers=auth(ruben), json={
        "name": "X", "ingredients": [{"product_id": p.id, "grams": 100}], "servings": 0,
    })
    assert r.status_code == 422


def test_friends_see_and_copy_the_steps(client, db, make_user):
    ruben, ana = make_user("Ruben"), make_user("Ana")
    _befriend(client, ruben, ana)
    p = _product(db, "Lenteja", 350)
    recipe = _create(client, ruben, p.id, steps=["Remojar", "Cocer"], servings=4, prep_minutes=5)

    shared = client.get(f"{API}/recipes/shared", headers=auth(ana)).json()
    assert shared[0]["steps"] == ["Remojar", "Cocer"]
    assert shared[0]["servings"] == 4

    r = client.post(f"{API}/recipes/{recipe['id']}/copy", headers=auth(ana))
    assert r.status_code == 201, r.text
    assert r.json()["steps"] == ["Remojar", "Cocer"]
    assert r.json()["prep_minutes"] == 5
