"""Muros Premium que se comprueban en el servidor, no solo en la interfaz.

Despensa, lista de la compra y los modos Premium de /goals se escondían en el
frontend pero el endpoint respondía a cualquiera. Y la fase de lanzamiento
(`settings.launch_open_access`) abre todo sin tocar el plan real de nadie.
"""
import pytest

from app.config import settings
from app.models.goals import UserGoals

from conftest import API, auth

GOALS = {"kcal": 2000, "protein": 150, "carbs": 250, "fat": 65}


@pytest.mark.parametrize("path", ["/inventory", "/shopping-list"])
def test_free_user_cannot_use_household_lists(client, make_user, path):
    ana = make_user("Ana")
    r = client.get(f"{API}{path}", headers=auth(ana))
    assert r.status_code == 402
    assert r.json()["detail"] == "premium_required"


@pytest.mark.parametrize("path", ["/inventory", "/shopping-list"])
def test_premium_user_can_use_household_lists(client, db, make_user, path):
    ana = make_user("Ana")
    ana.grandfathered = True
    db.commit()
    assert client.get(f"{API}{path}", headers=auth(ana)).status_code == 200


@pytest.mark.parametrize("extra", [{"macro_adjust_mode": "proportional"}, {"cheat_days_enabled": True}])
def test_free_user_cannot_turn_on_premium_goals(client, make_user, extra):
    ana = make_user("Ana")
    r = client.put(f"{API}/goals", json={**GOALS, **extra}, headers=auth(ana))
    assert r.status_code == 402


def test_free_user_can_still_save_plain_goals(client, make_user):
    ana = make_user("Ana")
    assert client.put(f"{API}/goals", json=GOALS, headers=auth(ana)).status_code == 200


def test_downgraded_user_keeps_saving_goals_with_old_premium_mode(client, db, make_user):
    """Quien ya lo tenía activado no se queda sin poder cambiar las kcal."""
    ana = make_user("Ana")
    db.add(UserGoals(user_id=ana.id, **GOALS, macro_adjust_mode="performance", cheat_days_enabled=True))
    db.commit()
    body = {**GOALS, "kcal": 1800, "macro_adjust_mode": "performance", "cheat_days_enabled": True}
    assert client.put(f"{API}/goals", json=body, headers=auth(ana)).status_code == 200


def test_launch_open_access_opens_everything_without_changing_the_plan(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "launch_open_access", True)
    ana = make_user("Ana")

    assert client.get(f"{API}/inventory", headers=auth(ana)).status_code == 200
    sub = client.get(f"{API}/users/me/subscription", headers=auth(ana)).json()
    assert sub["status"] == "free"
    assert sub["is_premium"] is True
    assert sub["launch_access"] is True


def test_launch_access_is_not_reported_for_real_premium(client, db, make_user, monkeypatch):
    monkeypatch.setattr(settings, "launch_open_access", True)
    ana = make_user("Ana")
    ana.grandfathered = True
    db.commit()
    sub = client.get(f"{API}/users/me/subscription", headers=auth(ana)).json()
    assert sub["status"] == "premium"
    assert sub["launch_access"] is False
