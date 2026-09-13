"""Tope semanal del comodín (cheat day).

Lo que se comprueba es el contrato que ve la app: cuántos van esta semana,
cuántos permite el usuario, y que el 409 salta solo al gastar uno *nuevo*
con la semana agotada — nunca al reactivar el de hoy ni al cancelarlo.
"""
from datetime import date, timedelta

from app.models.cheat_day import CheatDayLog
from app.models.goals import UserGoals

from conftest import API, auth


def _premium(db, user, per_week: int = 1):
    user.grandfathered = True  # el comodín es premium
    db.add(UserGoals(user_id=user.id, kcal=2000, protein=150, carbs=250, fat=65, cheat_days_per_week=per_week))
    db.commit()


def _log(db, user, day: date):
    db.add(CheatDayLog(user_id=user.id, used_date=day))
    db.commit()


def _monday(today: date) -> date:
    return today - timedelta(days=today.weekday())


def test_default_limit_is_one_per_week(client, db, make_user):
    ruben = make_user("Ruben")
    _premium(db, ruben)

    r = client.get(f"{API}/cheat-days/today", headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json() == {"active": False, "used_date": str(date.today()), "used_this_week": 0, "limit_per_week": 1}


def test_use_counts_toward_the_week(client, db, make_user):
    ruben = make_user("Ruben")
    _premium(db, ruben)

    r = client.post(f"{API}/cheat-days/use", headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["active"] is True
    assert r.json()["used_this_week"] == 1


def test_second_cheat_day_same_week_is_refused(client, db, make_user):
    today = date.today()
    if today.weekday() == 0:
        # En lunes la semana empieza hoy: el "otro día de esta semana" no existe aún.
        other = None
    else:
        other = _monday(today)
    ruben = make_user("Ruben")
    _premium(db, ruben)
    if other is None:
        _log(db, ruben, today)
        # Con el de hoy ya puesto, volver a activarlo no es gastar otro.
        r = client.post(f"{API}/cheat-days/use", headers=auth(ruben))
        assert r.status_code == 200, r.text
        return

    _log(db, ruben, other)
    r = client.post(f"{API}/cheat-days/use", headers=auth(ruben))
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "cheat_day_limit_reached"

    status = client.get(f"{API}/cheat-days/today", headers=auth(ruben)).json()
    assert status["active"] is False
    assert status["used_this_week"] == 1


def test_last_week_does_not_count(client, db, make_user):
    ruben = make_user("Ruben")
    _premium(db, ruben)
    _log(db, ruben, _monday(date.today()) - timedelta(days=1))  # domingo pasado

    r = client.post(f"{API}/cheat-days/use", headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["used_this_week"] == 1


def test_higher_limit_allows_more(client, db, make_user):
    today = date.today()
    if today.weekday() == 0:
        return  # sin otro día de esta semana que gastar
    ruben = make_user("Ruben")
    _premium(db, ruben, per_week=2)
    _log(db, ruben, _monday(today))

    r = client.post(f"{API}/cheat-days/use", headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["used_this_week"] == 2
    assert r.json()["limit_per_week"] == 2


def test_reactivating_today_is_idempotent(client, db, make_user):
    ruben = make_user("Ruben")
    _premium(db, ruben)
    client.post(f"{API}/cheat-days/use", headers=auth(ruben))

    r = client.post(f"{API}/cheat-days/use", headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["used_this_week"] == 1


def test_cancel_frees_the_slot(client, db, make_user):
    ruben = make_user("Ruben")
    _premium(db, ruben)
    client.post(f"{API}/cheat-days/use", headers=auth(ruben))

    r = client.delete(f"{API}/cheat-days/today", headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json() == {"active": False, "used_date": str(date.today()), "used_this_week": 0, "limit_per_week": 1}

    r = client.post(f"{API}/cheat-days/use", headers=auth(ruben))
    assert r.status_code == 200


def test_goals_reject_out_of_range_limit(client, db, make_user):
    ruben = make_user("Ruben")
    base = {"kcal": 2000, "protein": 150, "carbs": 250, "fat": 65}
    for bad in (0, 8):
        r = client.put(f"{API}/goals", json={**base, "cheat_days_per_week": bad}, headers=auth(ruben))
        assert r.status_code == 422, bad
    r = client.put(f"{API}/goals", json={**base, "cheat_days_per_week": 3}, headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["cheat_days_per_week"] == 3
