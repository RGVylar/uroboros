from conftest import API, auth

from app.models import Product
from app.models.product import ProductSource
from app.routers import products as products_router
from app.services.openfoodfacts import has_nutrition, kcal_per_100g


def test_kcal_from_kj_when_kcal_missing():
    assert kcal_per_100g({"energy-kj_100g": 418.4}) == 100.0
    assert kcal_per_100g({"energy_100g": 836.8}) == 200.0


def test_kcal_from_macros_when_zero():
    n = {"energy-kcal_100g": 0, "proteins_100g": 20, "carbohydrates_100g": 0, "fat_100g": 5}
    assert kcal_per_100g(n) == 125.0


def test_real_zero_stays_zero():
    n = {"energy-kcal_100g": 0, "proteins_100g": 0, "carbohydrates_100g": 0, "fat_100g": 0}
    assert kcal_per_100g(n) == 0
    assert has_nutrition(n)
    assert not has_nutrition({})


def _add(db, name, brand=None, kcal=165.0, source=ProductSource.openfoodfacts, barcode=None, p=31.0):
    prod = Product(
        name=name, brand=brand, barcode=barcode, calories_per_100g=kcal,
        protein_per_100g=p, carbs_per_100g=0, fat_per_100g=3.6, source=source,
    )
    db.add(prod)
    db.commit()
    return prod


def test_search_hides_empty_off_and_dedups(client, db, make_user, monkeypatch):
    async def _no_off(q, limit=20):
        return []
    monkeypatch.setattr(products_router, "search_by_name", _no_off)

    user = make_user("Ana")
    _add(db, "Pollo campero", "Carrefour", barcode="1")
    _add(db, "Pollo  campero", "carrefour", barcode="2")  # otro formato, mismos valores
    empty = Product(name="Pollo vacío", calories_per_100g=0, protein_per_100g=0,
                    carbs_per_100g=0, fat_per_100g=0, source=ProductSource.openfoodfacts, barcode="3")
    db.add(empty)
    db.commit()
    _add(db, "Pollo asado", kcal=200, p=25)

    r = client.get(f"{API}/products?q=pollo", headers=auth(user))
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "Pollo vacío" not in names
    assert sum(1 for n in names if "campero" in n) == 1
    assert "Pollo asado" in names
