"""GET /duel/me/awards — podios semanales en el ranking global.

Las medallas del perfil se dan contra toda la población con snapshot esa
semana (la misma que la fila «Tu constancia» de Ajustes), no contra los amigos
con los que se duela. Aquí sólo hay strangers: si el ranking fuera por amigos
no saldría ninguna medalla. Y el podio es la medalla: 3.º de 4 es bronce.
"""
from datetime import timedelta

from conftest import API, auth

from app.models.weekly_adherence import WeeklyAdherence
from app.services.duel_service import week_start_for


def _snapshot(db, user, weeks_ago, pct):
    from datetime import datetime, timezone

    ws = week_start_for(datetime.now(timezone.utc).date()) - timedelta(weeks=weeks_ago)
    db.add(WeeklyAdherence(user_id=user.id, week_start=ws, pct=pct, counted=5))
    db.commit()


def test_medals_come_from_the_global_ranking(client, db, make_user):
    me = make_user("Mugre")
    others = [make_user(f"Stranger{i}") for i in range(3)]

    # Hace 2 semanas: 1.º de 4 → oro. Hace 1: 3.º de 4 → bronce. Ser podio es
    # la medalla, sin más condiciones.
    _snapshot(db, me, 2, 90)
    for o, pct in zip(others, (60, 70, 80)):
        _snapshot(db, o, 2, pct)
    _snapshot(db, me, 1, 70)
    for o, pct in zip(others, (60, 80, 90)):
        _snapshot(db, o, 1, pct)

    r = client.get(f"{API}/duel/me/awards", headers=auth(me))
    assert r.status_code == 200, r.text
    a = r.json()
    assert (a["gold"], a["silver"], a["bronze"]) == (1, 0, 1)
    assert (a["best_rank"], a["best_total"]) == (1, 4)
    assert "pool" not in a


def test_tie_at_the_top_shares_first(client, db, make_user):
    me, rival = make_user("Mugre"), make_user("Rival")
    _snapshot(db, me, 1, 100)
    _snapshot(db, rival, 1, 100)

    a = client.get(f"{API}/duel/me/awards", headers=auth(me)).json()
    assert a["gold"] == 1
    assert (a["best_rank"], a["best_total"]) == (1, 2)


def test_no_past_weeks_means_no_metal(client, make_user):
    # La semana en curso la crea el propio endpoint (upsert del snapshot), así
    # que sólo lo pasado tiene que estar vacío.
    me = make_user("Mugre")
    a = client.get(f"{API}/duel/me/awards", headers=auth(me)).json()
    assert (a["gold"], a["silver"], a["bronze"]) == (0, 0, 0)
    assert (a["best_rank"], a["best_total"]) == (None, None)
