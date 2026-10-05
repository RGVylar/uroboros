"""PUT /goals: objetivo de pasos y guardados parciales."""
from conftest import API, auth

BASE = {"kcal": 2000, "protein": 150, "carbs": 250, "fat": 65}


def test_steps_goal_defaults_and_updates(client, make_user):
    ana = make_user("Ana")
    r = client.put(f"{API}/goals", json=BASE, headers=auth(ana))
    assert r.json()["steps_goal"] == 8000
    r = client.put(f"{API}/goals", json={**BASE, "steps_goal": 10000}, headers=auth(ana))
    assert r.json()["steps_goal"] == 10000


def test_partial_save_keeps_the_rest(client, db, make_user):
    """La página de Objetivos solo manda kcal, macros, agua y pasos: guardar
    ahí no puede apagar los cheat days ni el inventario."""
    ana = make_user("Ana")
    ana.grandfathered = True  # cheat days es premium
    db.commit()
    full = {**BASE, "cheat_days_enabled": True, "cheat_days_per_week": 3, "inventory_enabled": True, "steps_goal": 12000}
    assert client.put(f"{API}/goals", json=full, headers=auth(ana)).status_code == 200

    r = client.put(f"{API}/goals", json={**BASE, "kcal": 1800, "water_ml": 2500}, headers=auth(ana))
    g = r.json()
    assert g["kcal"] == 1800
    assert g["cheat_days_enabled"] is True
    assert g["cheat_days_per_week"] == 3
    assert g["inventory_enabled"] is True
    assert g["steps_goal"] == 12000


def test_steps_goal_out_of_range(client, make_user):
    ana = make_user("Ana")
    r = client.put(f"{API}/goals", json={**BASE, "steps_goal": -1}, headers=auth(ana))
    assert r.status_code == 422
