"""Who sees which recipe. The original complaint: adding a friend used to show
them everything already shared with the partner, because sharing was one boolean."""
from conftest import API, auth
from test_friendships import _befriend


def _recipe(client, owner, product, name, scope="none"):
    r = client.post(
        f"{API}/recipes",
        json={
            "name": name,
            "share_scope": scope,
            "ingredients": [{"product_id": product.id, "grams": 100}],
        },
        headers=auth(owner),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _shared_with_me(client, user) -> set[str]:
    r = client.get(f"{API}/recipes/shared", headers=auth(user))
    assert r.status_code == 200, r.text
    return {x["name"] for x in r.json()}


def test_partner_recipe_is_hidden_from_friends(client, make_user, make_product):
    ruben, pilar, silva = make_user("Ruben"), make_user("Pilar"), make_user("Silva")
    _befriend(client, ruben, pilar, kind="partner")
    _befriend(client, ruben, silva)
    product = make_product()

    _recipe(client, ruben, product, "Cena de los dos", scope="partner")
    _recipe(client, ruben, product, "Tarta para todos", scope="friends")
    _recipe(client, ruben, product, "Secreta", scope="none")

    assert _shared_with_me(client, pilar) == {"Cena de los dos", "Tarta para todos"}
    assert _shared_with_me(client, silva) == {"Tarta para todos"}


def test_adding_a_friend_does_not_expose_partner_recipes(client, make_user, make_product):
    """The exact scenario that started this: Pilar is the partner, Silva shows up later."""
    ruben, pilar, silva = make_user("Ruben"), make_user("Pilar"), make_user("Silva")
    _befriend(client, ruben, pilar, kind="partner")
    product = make_product()
    _recipe(client, ruben, product, "Nuestra receta", scope="partner")

    _befriend(client, ruben, silva)

    assert _shared_with_me(client, silva) == set()
    assert _shared_with_me(client, pilar) == {"Nuestra receta"}


def test_strangers_see_nothing(client, make_user, make_product):
    ruben, nadie = make_user("Ruben"), make_user("Nadie")
    product = make_product()
    _recipe(client, ruben, product, "Tarta para todos", scope="friends")

    assert _shared_with_me(client, nadie) == set()


def test_a_friend_cannot_open_a_partner_recipe_directly(client, make_user, make_product):
    ruben, pilar, silva = make_user("Ruben"), make_user("Pilar"), make_user("Silva")
    _befriend(client, ruben, pilar, kind="partner")
    _befriend(client, ruben, silva)
    product = make_product()
    rid = _recipe(client, ruben, product, "Cena de los dos", scope="partner")

    assert client.get(f"{API}/recipes/{rid}", headers=auth(silva)).status_code == 404
    assert client.get(f"{API}/recipes/{rid}", headers=auth(pilar)).status_code == 200


def test_a_friend_cannot_copy_a_partner_recipe(client, make_user, make_product):
    ruben, pilar, silva = make_user("Ruben"), make_user("Pilar"), make_user("Silva")
    _befriend(client, ruben, pilar, kind="partner")
    _befriend(client, ruben, silva)
    product = make_product()
    rid = _recipe(client, ruben, product, "Cena de los dos", scope="partner")

    assert client.post(f"{API}/recipes/{rid}/copy", headers=auth(silva)).status_code == 403
    assert client.post(f"{API}/recipes/{rid}/copy", headers=auth(pilar)).status_code == 201


def test_a_copy_starts_private(client, make_user, make_product):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _befriend(client, ruben, silva)
    product = make_product()
    rid = _recipe(client, ruben, product, "Tarta para todos", scope="friends")

    r = client.post(f"{API}/recipes/{rid}/copy", headers=auth(silva))
    assert r.json()["share_scope"] == "none", "someone else's sharing choice isn't inherited"


def test_new_recipes_default_to_shared_with_friends(client, make_user, make_product):
    """The API default: recipes are the social side of the app, so they go out to
    friends unless narrowed."""
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _befriend(client, ruben, silva)
    product = make_product()

    r = client.post(
        f"{API}/recipes",
        json={"name": "Sin scope", "ingredients": [{"product_id": product.id, "grams": 100}]},
        headers=auth(ruben),
    )
    assert r.json()["share_scope"] == "friends"
    assert _shared_with_me(client, silva) == {"Sin scope"}


def test_narrowing_the_scope_takes_access_away(client, make_user, make_product):
    ruben, pilar, silva = make_user("Ruben"), make_user("Pilar"), make_user("Silva")
    _befriend(client, ruben, pilar, kind="partner")
    _befriend(client, ruben, silva)
    product = make_product()
    rid = _recipe(client, ruben, product, "Tarta", scope="friends")
    assert _shared_with_me(client, silva) == {"Tarta"}

    r = client.patch(f"{API}/recipes/{rid}/share", json={"scope": "partner"}, headers=auth(ruben))
    assert r.status_code == 200

    assert _shared_with_me(client, silva) == set()
    assert _shared_with_me(client, pilar) == {"Tarta"}


def test_only_the_owner_picks_the_scope(client, make_user, make_product):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _befriend(client, ruben, silva)
    product = make_product()
    rid = _recipe(client, ruben, product, "Tarta", scope="friends")

    r = client.patch(f"{API}/recipes/{rid}/share", json={"scope": "none"}, headers=auth(silva))
    assert r.status_code == 404
