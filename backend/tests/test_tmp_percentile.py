"""Scratch check for /duel/me/percentile — NOT to be committed."""
from datetime import datetime, time, timedelta, timezone

import pytest

from app.models.diary import DiaryEntry, MealType
from app.models.weekly_adherence import WeeklyAdherence
from app.services.duel_service import week_start_for
from tests.conftest import API, auth

TODAY = datetime.now(timezone.utc).date()
WS = week_start_for(TODAY)
PAST_DAYS = (TODAY - WS).days  # días ya cerrados de esta semana


def _log(db, user_id, product_id, days):
    """Registra `days` días cerrados de esta semana (sin objetivo → cuentan como hit)."""
    for i in range(days):
        db.add(DiaryEntry(
            user_id=user_id, product_id=product_id, grams=100, meal_type=MealType.snack,
            calories=500, protein=10, carbs=50, fat=5,
            consumed_at=datetime.combine(WS + timedelta(days=i), time(12, 0), tzinfo=timezone.utc),
        ))
    db.commit()


def _snap(db, user_id, week_start, pct):
    db.add(WeeklyAdherence(user_id=user_id, week_start=week_start, pct=pct, counted=3))
    db.commit()


@pytest.mark.skipif(PAST_DAYS < 2, reason="necesita al menos 2 días cerrados esta semana")
def test_medalla_solo_si_se_gana_y_hueco_hasta_el_de_delante(db, client, make_user, make_product):
    me = make_user("Mugre")
    others = [make_user(f"U{i}") for i in range(3)]
    product = make_product()
    # Registro la mitad de los días cerrados → ~50 %, tercero de cuatro.
    _log(db, me.id, product.id, PAST_DAYS // 2)
    mi_pct = round((PAST_DAYS // 2) / PAST_DAYS * 100)
    _snap(db, others[0].id, WS, 100)
    _snap(db, others[1].id, WS, mi_pct + 5)
    _snap(db, others[2].id, WS, 1)

    r = client.get(f"{API}/duel/me/percentile", headers=auth(me)).json()
    print("\n3.º de 4 →", r)
    assert (r["pct"], r["rank"], r["active_users"]) == (mi_pct, 3, 4)
    assert r["medal"] is None, "3.º de 4 no es un bronce"
    assert r["gap_to_next"] == 5, "puntos hasta el 2.º"


@pytest.mark.skipif(PAST_DAYS < 2, reason="necesita al menos 2 días cerrados esta semana")
def test_primero_lleva_oro_y_no_tiene_hueco(db, client, make_user, make_product):
    me = make_user("Karma")
    other = make_user("Otro")
    product = make_product()
    _log(db, me.id, product.id, PAST_DAYS)
    _snap(db, other.id, WS, 40)

    r = client.get(f"{API}/duel/me/percentile", headers=auth(me)).json()
    print("\n1.º de 2 →", r)
    assert (r["pct"], r["rank"], r["medal"]) == (100, 1, 1)
    assert r["gap_to_next"] is None


@pytest.mark.skipif(PAST_DAYS < 2, reason="necesita al menos 2 días cerrados esta semana")
def test_segundo_de_cuatro_lleva_plata_pero_tercero_no(db, client, make_user, make_product):
    me = make_user("Kishyl")
    others = [make_user(f"U{i}") for i in range(3)]
    product = make_product()
    _log(db, me.id, product.id, PAST_DAYS)  # 100 %, empatado arriba con nadie
    _snap(db, others[0].id, WS, 100)        # empate: los dos son 1.º
    _snap(db, others[1].id, WS, 30)
    _snap(db, others[2].id, WS, 10)

    r = client.get(f"{API}/duel/me/percentile", headers=auth(me)).json()
    print("\nempate arriba de 4 →", r)
    assert r["rank"] == 1 and r["medal"] == 1
