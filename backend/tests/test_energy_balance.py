"""Tendencia del peso, gasto real y propuesta semanal de objetivos."""
from datetime import date, datetime, time, timedelta, timezone

from app.models import DiaryEntry, UserGoals, WeightLog
from app.services.energy_balance import (
    Macros, iso_week, propose, slope_kg_per_day, weekly_rate, weight_trend,
)

from conftest import API, auth

TODAY = date(2026, 10, 12)  # lunes
CURRENT = Macros(kcal=2000, protein=150, carbs=200, fat=67)


def _weighins(start_kg: float, kg_per_week: float, days: int = 21, every: int = 2):
    return [(TODAY - timedelta(days=days - i), start_kg + kg_per_week / 7 * i) for i in range(0, days, every)]


def _intake(kcal: float, days: int = 21):
    return {TODAY - timedelta(days=i): kcal for i in range(1, days + 1)}


# ── Tendencia ────────────────────────────────────────────────────────────────

def test_trend_smooths_a_single_spike():
    d0 = date(2026, 10, 1)
    pts = weight_trend([(d0, 80), (d0 + timedelta(days=1), 80), (d0 + timedelta(days=2), 82), (d0 + timedelta(days=3), 80)])
    assert pts[2].weight == 82
    assert pts[2].trend < 80.3  # un día de +2 kg mueve la tendencia 0,2


def test_trend_counts_gaps_as_several_days():
    d0 = date(2026, 10, 1)
    one = weight_trend([(d0, 80), (d0 + timedelta(days=1), 78)])[-1].trend
    gap = weight_trend([(d0, 80), (d0 + timedelta(days=10), 78)])[-1].trend
    assert gap < one  # tras 10 días sin pesarse, el pesaje nuevo pesa más


def test_same_day_weighins_are_averaged():
    d0 = date(2026, 10, 1)
    pts = weight_trend([(d0, 80), (d0, 81)])
    assert len(pts) == 1 and pts[0].weight == 80.5


def test_weekly_rate_and_slope():
    w = _weighins(80, -0.5)
    assert abs(slope_kg_per_day(w) * 7 - (-0.5)) < 0.01
    rate = weekly_rate(weight_trend(w))
    assert rate is not None and rate < 0


# ── Propuesta ────────────────────────────────────────────────────────────────

def test_not_enough_data():
    p = propose(CURRENT, "lose", _weighins(80, -0.5, days=7), _intake(2000, days=7))
    assert p.status == "not_enough_data"
    assert p.proposed is None


def test_half_logged_days_dont_count():
    intake = _intake(2000)
    for d in list(intake)[:15]:
        intake[d] = 600  # apuntado a medias
    p = propose(CURRENT, "maintain", _weighins(80, 0), intake)
    assert p.status == "not_enough_data"
    assert p.logged_days == 6


def test_real_expenditure_from_intake_and_weight():
    # Come 2000 y baja 0,5 kg/semana → gasta ~2000 + 0,5·7700/7 = 2550
    p = propose(CURRENT, "maintain", _weighins(80, -0.5), _intake(2000))
    assert abs(p.tdee - 2550) <= 20


def test_maintain_proposes_more_when_losing_without_wanting_to():
    p = propose(CURRENT, "maintain", _weighins(80, -0.5), _intake(2000))
    assert p.status == "proposal"
    # Pediría +550, pero se mueve como mucho 300 por semana
    assert p.proposed.kcal == 2300
    assert p.proposed.protein == CURRENT.protein
    total = p.proposed.protein * 4 + p.proposed.carbs * 4 + p.proposed.fat * 9
    assert abs(total - p.proposed.kcal) < 15


def test_lose_on_track():
    # Quiere perder, come 2000 y baja ~0,36 kg/semana (déficit ~400): va bien
    p = propose(CURRENT, "lose", _weighins(80, -400 * 7 / 7700), _intake(2000))
    assert p.status == "on_track"


def test_gain_when_stuck_proposes_more():
    p = propose(CURRENT, "gain", _weighins(70, 0), _intake(2000))
    assert p.status == "proposal"
    assert p.proposed.kcal == 2300


def test_needs_objective():
    p = propose(CURRENT, None, _weighins(80, -0.5), _intake(2000))
    assert p.status == "need_objective"
    assert p.tdee is not None


def test_absurd_numbers_are_not_proposed():
    # Baja 3 kg por semana comiendo 2000: báscula nueva o días sin apuntar
    p = propose(CURRENT, "maintain", _weighins(80, -3), _intake(2000))
    assert p.status == "unreliable"


def test_never_below_minimum():
    low = Macros(kcal=1300, protein=100, carbs=120, fat=45)
    # Gasta 1300 y quiere perder: pediría 900, se queda en 1200
    p = propose(low, "lose", _weighins(80, 0), _intake(1300))
    assert p.status == "proposal"
    assert p.proposed.kcal == 1200


# ── Endpoints ────────────────────────────────────────────────────────────────

def test_proposal_apply_and_hide_until_next_week(client, db, make_user, make_product):
    ana = make_user("Ana")
    ana.grandfathered = True
    _seed_with_product(db, ana, make_product)

    r = client.get(f"{API}/goals/proposal", headers=auth(ana)).json()
    assert r["status"] == "proposal" and r["locked"] is False
    assert r["proposed"]["kcal"] == 2300

    g = client.post(f"{API}/goals/proposal", json={"action": "apply"}, headers=auth(ana)).json()
    assert g["kcal"] == 2300
    r = client.get(f"{API}/goals/proposal", headers=auth(ana)).json()
    assert r["status"] != "proposal"


def test_dismiss_hides_it_for_the_week(client, db, make_user, make_product):
    ana = make_user("Ana")
    ana.grandfathered = True
    _seed_with_product(db, ana, make_product)
    client.post(f"{API}/goals/proposal", json={"action": "dismiss"}, headers=auth(ana))
    r = client.get(f"{API}/goals/proposal", headers=auth(ana)).json()
    assert r["status"] == "answered"
    g = db.get(UserGoals, ana.id)
    db.refresh(g)
    assert g.kcal == 2000 and g.adapt_week == iso_week(datetime.now(timezone.utc).date())


def test_free_user_sees_there_is_one_but_not_the_numbers(client, db, make_user, make_product):
    ana = make_user("Ana")
    _seed_with_product(db, ana, make_product)
    r = client.get(f"{API}/goals/proposal", headers=auth(ana)).json()
    assert r["status"] == "proposal" and r["locked"] is True
    assert "proposed" not in r and "tdee" not in r
    assert client.post(f"{API}/goals/proposal", json={"action": "apply"}, headers=auth(ana)).status_code == 402


def test_profile_is_saved_and_returned(client, db, make_user):
    ana = make_user("Ana")
    db.add(UserGoals(user_id=ana.id, kcal=2000, protein=150, carbs=200, fat=67))
    db.commit()
    r = client.patch(f"{API}/goals/profile", json={"objective": "lose", "sex": "female", "height_cm": 165},
                     headers=auth(ana))
    assert r.status_code == 200
    g = client.get(f"{API}/goals", headers=auth(ana)).json()
    assert g["objective"] == "lose" and g["sex"] == "female" and g["height_cm"] == 165
    assert client.patch(f"{API}/goals/profile", json={"objective": "bulk"}, headers=auth(ana)).status_code == 422


def test_weight_trend_endpoint(client, db, make_user):
    ana = make_user("Ana")
    now = datetime.now(timezone.utc)
    for i, w in enumerate([81, 80.6, 80.9, 80.2, 80.0, 79.8]):
        db.add(WeightLog(user_id=ana.id, weight=w, logged_at=now - timedelta(days=12 - 2 * i)))
    db.commit()
    r = client.get(f"{API}/weight/trend", headers=auth(ana)).json()
    assert len(r["points"]) == 6
    assert r["latest_trend"] is not None and r["latest_trend"] > 79.8  # va con retraso
    assert r["weekly_rate"] < 0


def _seed_with_product(db, user, make_product):
    """21 días comiendo 2000 kcal y bajando 0,5 kg/semana, con objetivo mantener."""
    product = make_product()
    db.add(UserGoals(user_id=user.id, kcal=2000, protein=150, carbs=200, fat=67, objective="maintain"))
    today = datetime.now(timezone.utc).date()
    for i in range(1, 22):
        at = datetime.combine(today - timedelta(days=i), time(13), tzinfo=timezone.utc)
        db.add(DiaryEntry(user_id=user.id, product_id=product.id, grams=100, calories=2000, protein=150,
                          carbs=200, fat=67, meal_type="lunch", consumed_at=at))
        if i % 2:
            db.add(WeightLog(user_id=user.id, weight=80 + 0.5 / 7 * i, logged_at=at))
    db.commit()
