"""Alimentos genéricos: salen los primeros, en el idioma del cliente y no se
pueden editar."""
import pytest
from conftest import API, auth

from app.data.generic_foods import GENERIC_FOODS
from app.models import Product
from app.models.product import ProductSource
from app.routers import products as products_router
from app.services.generic_foods import sync_generic_foods


@pytest.fixture()
def generics(db, monkeypatch):
    async def _no_off(q, limit=20):
        return []
    monkeypatch.setattr(products_router, "search_by_name", _no_off)
    sync_generic_foods(db.connection())
    db.commit()


def _search(client, user, q, lang=None):
    headers = auth(user) | ({"X-Lang": lang} if lang else {})
    r = client.get(f"{API}/products", params={"q": q}, headers=headers)
    assert r.status_code == 200
    return r.json()


def test_catalogue_is_consistent():
    keys = [row[0] for row in GENERIC_FOODS]
    assert len(keys) == len(set(keys))
    alcohol = {"beer", "red_wine", "white_wine"}
    for key, es, en, pt, kcal, p, c, f, unit in GENERIC_FOODS:
        assert es and en and pt, key
        assert unit in ("g", "ml", "unit"), key
        if key in alcohol:
            continue
        # Las kcal tienen que cuadrar con los macros (4/4/9, con margen para
        # la fibra y el redondeo). Pilla una errata en una fila.
        assert abs(p * 4 + c * 4 + f * 9 - kcal) <= max(25, kcal * 0.2), key


def test_sync_is_idempotent(db, generics):
    first = {p.generic_key: p.id for p in db.query(Product).filter(Product.generic_key.isnot(None))}
    sync_generic_foods(db.connection())
    db.commit()
    again = {p.generic_key: p.id for p in db.query(Product).filter(Product.generic_key.isnot(None))}
    assert first == again
    assert len(first) == len(GENERIC_FOODS)


def test_generic_comes_before_brands(client, db, make_user, generics):
    user = make_user("Ana")
    db.add(Product(name="Pechuga de pavo", brand="ElPozo", barcode="84", calories_per_100g=95,
                   protein_per_100g=18, carbs_per_100g=1.5, fat_per_100g=1.8,
                   source=ProductSource.openfoodfacts))
    db.commit()

    results = _search(client, user, "pavo")
    assert results[0]["source"] == "generic"
    assert "pavo" in results[0]["name"].lower()
    assert any(r["brand"] == "ElPozo" for r in results)


def test_search_ignores_accents_and_word_order(client, make_user, generics):
    user = make_user("Ana")
    assert _search(client, user, "platano")[0]["name"] == "Plátano"
    names = [r["name"] for r in _search(client, user, "pavo pechuga")]
    assert "Pechuga de pavo (cruda)" in names


def test_name_follows_client_language(client, make_user, generics):
    user = make_user("Ana")
    assert _search(client, user, "turkey", lang="en")[0]["name"].startswith("Turkey breast")
    # Se encuentra por cualquier idioma, pero se muestra en el del cliente.
    assert "peru" in _search(client, user, "pavo", lang="pt")[0]["name"]
    assert "Peito de frango (cru)" in [r["name"] for r in _search(client, user, "frango", lang="pt")]


def test_generic_is_read_only(client, db, make_user, generics):
    user = make_user("Ana")
    product = db.query(Product).filter_by(generic_key="banana").one()
    r = client.patch(f"{API}/products/{product.id}", json={"calories_per_100g": 1}, headers=auth(user))
    assert r.status_code == 403


def test_word_prefix_not_substring(client, make_user, generics):
    user = make_user("Ana")
    names = [r["name"] for r in _search(client, user, "pollo")]
    assert "Repollo" not in names
    assert "Pechuga de pollo (cruda)" in names
    # A medio escribir también vale.
    assert "Pechuga de pollo (cruda)" in [r["name"] for r in _search(client, user, "pech")]


def test_generic_catalogue_for_offline(client, db, make_user, generics):
    """La app se baja el catálogo entero para buscar sin conexión: todos los
    genéricos, ninguna marca, en orden de catálogo y en el idioma pedido."""
    user = make_user("Ana")
    db.add(Product(name="Pechuga de pavo", brand="ElPozo", barcode="84", calories_per_100g=95,
                   protein_per_100g=18, carbs_per_100g=1.5, fat_per_100g=1.8,
                   source=ProductSource.openfoodfacts))
    db.commit()

    r = client.get(f"{API}/products/generic", headers=auth(user) | {"X-Lang": "en"})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == len(GENERIC_FOODS)
    assert all(p["source"] == "generic" for p in rows)
    assert rows[0]["name"] == GENERIC_FOODS[0][2]
