"""GET/PATCH /users/me/modules y POST /users/me/tips/{id}/seen."""
from conftest import API, auth

BASE = {"kcal": 2000, "protein": 150, "carbs": 250, "fat": 65}


def test_defaults_without_goals(client, make_user):
    ana = make_user("Ana")
    m = client.get(f"{API}/users/me/modules", headers=auth(ana)).json()
    assert m["water"] is True and m["weight"] is True and m["supplements"] is True
    assert m["mood"] is False
    assert m["creatine"] is False and m["cheat_days"] is False and m["inventory"] is False


def test_partial_patch_keeps_the_rest(client, make_user):
    ana = make_user("Ana")
    client.patch(f"{API}/users/me/modules", json={"mood": True}, headers=auth(ana))
    m = client.patch(f"{API}/users/me/modules", json={"water": False}, headers=auth(ana)).json()
    assert m["mood"] is True
    assert m["water"] is False
    assert m["weight"] is True


def test_goal_modules_write_to_goals(client, make_user):
    """El inventario vive en user_goals: el diario y /add lo leen ahí."""
    ana = make_user("Ana")
    client.put(f"{API}/goals", json={**BASE, "kcal": 1800}, headers=auth(ana))
    m = client.patch(f"{API}/users/me/modules", json={"inventory": True}, headers=auth(ana)).json()
    assert m["inventory"] is True
    g = client.get(f"{API}/goals", headers=auth(ana)).json()
    assert g["inventory_enabled"] is True
    assert g["kcal"] == 1800  # no pisa los objetivos


def test_creatine_is_no_longer_a_module(client, make_user):
    """Desde la 0080 es un suplemento: las APK viejas la mandan y se ignora."""
    ana = make_user("Ana")
    m = client.patch(f"{API}/users/me/modules", json={"creatine": True}, headers=auth(ana)).json()
    assert m["creatine"] is False


def test_goal_module_without_goals_creates_them(client, make_user):
    ana = make_user("Ana")
    r = client.patch(f"{API}/users/me/modules", json={"inventory": True}, headers=auth(ana))
    assert r.status_code == 200
    assert client.get(f"{API}/goals", headers=auth(ana)).json()["inventory_enabled"] is True


def test_cheat_days_need_premium_to_turn_on(client, db, make_user):
    ana = make_user("Ana")
    r = client.patch(f"{API}/users/me/modules", json={"cheat_days": True}, headers=auth(ana))
    assert r.status_code == 402
    ana.grandfathered = True
    db.commit()
    r = client.patch(f"{API}/users/me/modules", json={"cheat_days": True}, headers=auth(ana))
    assert r.json()["cheat_days"] is True


def test_cheat_days_can_be_turned_off_without_premium(client, db, make_user):
    ana = make_user("Ana")
    ana.grandfathered = True
    db.commit()
    client.patch(f"{API}/users/me/modules", json={"cheat_days": True}, headers=auth(ana))
    ana.grandfathered = False
    db.commit()
    r = client.patch(f"{API}/users/me/modules", json={"cheat_days": False}, headers=auth(ana))
    assert r.status_code == 200 and r.json()["cheat_days"] is False


def test_tips_seen_once(client, make_user):
    ana = make_user("Ana")
    assert client.get(f"{API}/auth/me", headers=auth(ana)).json()["seen_tips"] == []
    client.post(f"{API}/users/me/tips/duel/seen", headers=auth(ana))
    u = client.post(f"{API}/users/me/tips/duel/seen", headers=auth(ana)).json()
    assert u["seen_tips"] == ["duel"]
