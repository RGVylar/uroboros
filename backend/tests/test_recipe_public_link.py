"""Enlace público de una receta (/r/<código>): compartirla fuera de la app.

Solo la dueña lo crea o lo retira; la página no pide sesión y lleva la tarjeta
Open Graph; desde ella cualquiera con cuenta se guarda una copia privada.
"""
from conftest import API, auth
from test_recipe_portion import _product


def _recipe(client, owner, product_id, **extra):
    body = {"name": "Pollo al curry", "share_scope": "none", "servings": 2,
            "ingredients": [{"product_id": product_id, "grams": 220}], **extra}
    r = client.post(f"{API}/recipes", json=body, headers=auth(owner))
    assert r.status_code == 201, r.text
    return r.json()


def _link(client, owner, recipe_id):
    r = client.post(f"{API}/recipes/{recipe_id}/public-link", headers=auth(owner))
    assert r.status_code == 200, r.text
    return r.json()["public_code"]


def test_new_recipe_has_no_link_and_owner_creates_a_stable_one(client, db, make_user):
    ruben = make_user("Ruben")
    p = _product(db, "Pechuga", 120)
    recipe = _recipe(client, ruben, p.id)
    assert recipe["public_code"] is None
    code = _link(client, ruben, recipe["id"])
    assert code and len(code) == 8
    # Compartirla otra vez no cambia el enlace ya enviado.
    assert _link(client, ruben, recipe["id"]) == code


def test_only_the_owner_creates_or_removes_the_link(client, db, make_user):
    ruben, ana = make_user("Ruben"), make_user("Ana")
    p = _product(db, "Pechuga", 120)
    recipe = _recipe(client, ruben, p.id)
    r = client.post(f"{API}/recipes/{recipe['id']}/public-link", headers=auth(ana))
    assert r.status_code == 404
    _link(client, ruben, recipe["id"])
    r = client.delete(f"{API}/recipes/{recipe['id']}/public-link", headers=auth(ana))
    assert r.status_code == 404


def test_page_is_public_with_open_graph_and_mentions(client, db, make_user):
    ruben = make_user("Ruben")
    p = _product(db, "Pechuga", 120)
    recipe = _recipe(client, ruben, p.id, steps=[f"Dora la @[Pechuga]({p.id}) a fuego fuerte"])
    code = _link(client, ruben, recipe["id"])

    r = client.get(f"/r/{code}?lang=es")
    assert r.status_code == 200
    html = r.text
    assert '<meta property="og:title" content="Pollo al curry">' in html
    # 220 g a 120 kcal/100 g = 264 kcal; entre 2 raciones, 132.
    assert "132 kcal" in html
    assert '<span class="chip">Pechuga<span class="q" data-g="220"' in html
    assert f"/recipes?importar={code}" in html


def test_page_escapes_user_text(client, db, make_user):
    ruben = make_user("Ruben")
    p = _product(db, "Pechuga", 120)
    recipe = _recipe(client, ruben, p.id, name="<script>alert(1)</script>",
                     steps=["<img src=x onerror=alert(1)>"])
    code = _link(client, ruben, recipe["id"])
    html = client.get(f"/r/{code}").text
    assert "<script>alert(1)</script>" not in html
    assert "<img src=x" not in html


def test_removed_link_shows_not_found(client, db, make_user):
    ruben = make_user("Ruben")
    p = _product(db, "Pechuga", 120)
    recipe = _recipe(client, ruben, p.id)
    code = _link(client, ruben, recipe["id"])
    r = client.delete(f"{API}/recipes/{recipe['id']}/public-link", headers=auth(ruben))
    assert r.status_code == 200 and r.json()["public_code"] is None
    r = client.get(f"/r/{code}")
    assert r.status_code == 404
    assert "ya no está compartida" in r.text


def test_anyone_with_an_account_saves_a_private_copy(client, db, make_user):
    ruben, marta = make_user("Ruben"), make_user("Marta")
    p = _product(db, "Pechuga", 120)
    recipe = _recipe(client, ruben, p.id, steps=["Uno", "Dos"])
    code = _link(client, ruben, recipe["id"])

    r = client.post(f"{API}/recipes/public/{code}/copy", headers=auth(marta))
    assert r.status_code == 201, r.text
    copy = r.json()
    assert copy["owner_id"] == marta.id and copy["id"] != recipe["id"]
    assert copy["steps"] == ["Uno", "Dos"]
    # La copia no hereda ni el enlace ni el círculo de quien la compartió.
    assert copy["public_code"] is None and copy["share_scope"] == "none"


def test_saving_your_own_recipe_does_not_duplicate_it(client, db, make_user):
    ruben = make_user("Ruben")
    p = _product(db, "Pechuga", 120)
    recipe = _recipe(client, ruben, p.id)
    code = _link(client, ruben, recipe["id"])
    r = client.post(f"{API}/recipes/public/{code}/copy", headers=auth(ruben))
    assert r.json()["id"] == recipe["id"]
    assert len(client.get(f"{API}/recipes", headers=auth(ruben)).json()) == 1


def test_copy_of_unknown_code_is_404(client, make_user):
    marta = make_user("Marta")
    r = client.post(f"{API}/recipes/public/nopenope/copy", headers=auth(marta))
    assert r.status_code == 404


def test_card_says_one_ingredient_in_singular(client, db, make_user):
    ruben = make_user("Ruben")
    p = _product(db, "Pure", 48)
    recipe = _recipe(client, ruben, p.id, servings=None)
    code = _link(client, ruben, recipe["id"])
    html = client.get(f"/r/{code}?lang=es").text
    assert "· 1 ingrediente\"" in html
