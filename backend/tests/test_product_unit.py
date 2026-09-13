"""products.unit: en qué se mide un producto ('g' | 'ml' | 'unit').

Nulo = como siempre, el cliente lo adivina por el nombre. Solo se comprueba
el contrato del campo: se guarda, se devuelve, se edita y rechaza basura.
"""
from conftest import API, auth

BASE = {"name": "Huevo", "calories_per_100g": 70, "protein_per_100g": 6, "carbs_per_100g": 0.5, "fat_per_100g": 5}


def test_unit_defaults_to_null(client, make_user):
    ruben = make_user("Ruben")
    r = client.post(f"{API}/products", json=BASE, headers=auth(ruben))
    assert r.status_code == 201, r.text
    assert r.json()["unit"] is None


def test_unit_is_stored_and_returned(client, make_user):
    ruben = make_user("Ruben")
    r = client.post(f"{API}/products", json={**BASE, "unit": "unit"}, headers=auth(ruben))
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert r.json()["unit"] == "unit"

    r = client.get(f"{API}/products/{pid}", headers=auth(ruben))
    assert r.json()["unit"] == "unit"


def test_unit_can_be_changed(client, make_user):
    ruben = make_user("Ruben")
    pid = client.post(f"{API}/products", json={**BASE, "unit": "g"}, headers=auth(ruben)).json()["id"]
    r = client.patch(f"{API}/products/{pid}", json={"unit": "ml"}, headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["unit"] == "ml"


def test_unknown_unit_is_rejected(client, make_user):
    ruben = make_user("Ruben")
    r = client.post(f"{API}/products", json={**BASE, "unit": "kg"}, headers=auth(ruben))
    assert r.status_code == 422


def test_diary_entry_carries_product_unit(client, make_user):
    """El diario enseña "2 ud" a partir de product.unit: tiene que viajar en la entrada."""
    ruben = make_user("Ruben")
    pid = client.post(f"{API}/products", json={**BASE, "unit": "unit"}, headers=auth(ruben)).json()["id"]
    r = client.post(f"{API}/diary", json={"product_id": pid, "grams": 200, "meal_type": "breakfast", "consumed_at": "2026-09-13T09:00:00Z"}, headers=auth(ruben))
    assert r.status_code in (200, 201), r.text
    entry = r.json()[0]  # POST /diary devuelve la lista de entradas creadas (la tuya y, si toca, la de la pareja)
    assert entry["product"]["unit"] == "unit"
    assert entry["calories"] == 140  # 2 unidades × 70 kcal: 1 ud = 100 g internos
