from conftest import API, auth

from app.models import Product
from app.models.product import ProductSource
from app.routers import products as products_router
from app.services.openfoodfacts import OFFProduct, parse_measure


def test_measure_from_package():
    # Así llega una lata de refresco y un pack de yogures desde OFF.
    can = {"product_quantity": 330, "product_quantity_unit": "ml",
           "serving_quantity": 330, "serving_quantity_unit": "ml"}
    assert parse_measure(can) == ("ml", 330, 330)
    yogurt = {"product_quantity": "750", "product_quantity_unit": "g",
              "serving_quantity": "125", "serving_quantity_unit": "g"}
    assert parse_measure(yogurt) == ("g", 750, 125)


def test_measure_falls_back_to_serving_then_category():
    assert parse_measure({"serving_quantity": 200, "serving_quantity_unit": "ml"})[0] == "ml"
    assert parse_measure({"categories_tags": ["en:beverages", "en:sodas"]}) == ("ml", None, None)
    # Café molido: está en bebidas, pero el envase en gramos manda.
    coffee = {"product_quantity": 250, "product_quantity_unit": "g", "categories_tags": ["en:beverages"]}
    assert parse_measure(coffee)[0] == "g"


def test_measure_unknown_and_junk():
    assert parse_measure({}) == (None, None, None)
    assert parse_measure({"product_quantity": 0, "product_quantity_unit": "g"}) == ("g", None, None)
    assert parse_measure({"product_quantity": 99999, "product_quantity_unit": "g"}) == ("g", None, None)


def _off(barcode, name="Aquarius limón", **kw):
    return OFFProduct(barcode=barcode, name=name, brand="Coca-Cola", kcal=11,
                      protein=0, carbs=2.6, fat=0, **kw)


def test_search_stores_and_backfills_measure(client, db, make_user, monkeypatch):
    async def _fake_off(q, limit=20):
        return [_off("111", "Aquarius zero", unit="ml", package_qty=500, serving_qty=250),
                _off("222", unit="ml", package_qty=330),
                _off("333", unit="ml", package_qty=500)]
    monkeypatch.setattr(products_router, "search_by_name", _fake_off)

    user = make_user("Ana")
    # Guardado antes de pedir medidas a OFF.
    old = Product(name="Aquarius limón", brand="Coca-Cola", barcode="222", calories_per_100g=11,
                  protein_per_100g=0, carbs_per_100g=2.6, fat_per_100g=0,
                  source=ProductSource.openfoodfacts)
    # Con unidad puesta a mano: no se pisa.
    edited = Product(name="Aquarius naranja", barcode="333", calories_per_100g=11,
                     protein_per_100g=0, carbs_per_100g=2.6, fat_per_100g=0, unit="unit",
                     source=ProductSource.edited)
    db.add_all([old, edited])
    db.commit()

    r = client.get(f"{API}/products?q=aquarius", headers=auth(user))
    assert r.status_code == 200
    new = db.query(Product).filter_by(barcode="111").one()
    assert (new.unit, new.package_qty, new.serving_qty) == ("ml", 500, 250)
    db.refresh(old)
    assert (old.unit, old.package_qty) == ("ml", 330)
    db.refresh(edited)
    assert edited.unit == "unit" and edited.package_qty is None
    out = {p["barcode"]: p for p in r.json()}
    assert out["111"]["serving_qty"] == 250
