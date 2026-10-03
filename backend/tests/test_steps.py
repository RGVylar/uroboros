"""Pasos diarios sincronizados desde Health Connect."""
from conftest import API, auth


def _sync(client, user, days):
    r = client.put(f"{API}/steps", json={"days": days}, headers=auth(user))
    assert r.status_code == 200, r.text
    return r.json()


def test_sync_then_list(client, make_user):
    ruben = make_user("Ruben")
    _sync(client, ruben, [{"day": "2026-10-01", "steps": 8000}, {"day": "2026-10-02", "steps": 12000}])
    r = client.get(f"{API}/steps?start=2026-10-01&end=2026-10-03", headers=auth(ruben))
    assert r.status_code == 200
    assert [(d["day"], d["steps"]) for d in r.json()] == [("2026-10-01", 8000), ("2026-10-02", 12000)]


def test_resync_overwrites_the_day(client, make_user):
    ruben = make_user("Ruben")
    _sync(client, ruben, [{"day": "2026-10-03", "steps": 1500}])
    _sync(client, ruben, [{"day": "2026-10-03", "steps": 6400}])
    r = client.get(f"{API}/steps?start=2026-10-03&end=2026-10-03", headers=auth(ruben))
    assert [d["steps"] for d in r.json()] == [6400]


def test_steps_are_private(client, make_user):
    ruben, ana = make_user("Ruben"), make_user("Ana")
    _sync(client, ruben, [{"day": "2026-10-03", "steps": 5000}])
    r = client.get(f"{API}/steps?start=2026-10-03&end=2026-10-03", headers=auth(ana))
    assert r.json() == []


def test_rejects_negative_and_bad_range(client, make_user):
    ruben = make_user("Ruben")
    r = client.put(f"{API}/steps", json={"days": [{"day": "2026-10-03", "steps": -1}]}, headers=auth(ruben))
    assert r.status_code == 422
    r = client.get(f"{API}/steps?start=2026-10-03&end=2026-10-01", headers=auth(ruben))
    assert r.status_code == 422


def test_account_deletion_removes_steps(client, db, make_user):
    from app.models import DailySteps

    ruben = make_user("Ruben")
    _sync(client, ruben, [{"day": "2026-10-03", "steps": 5000}])
    r = client.delete(f"{API}/users/me", headers=auth(ruben))
    assert r.status_code == 204
    assert db.query(DailySteps).count() == 0
