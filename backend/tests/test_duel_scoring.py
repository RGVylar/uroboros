"""Puntuación graduada de la adherencia (duel_service).

Cada día contado vale 0–100: hasta 70 por calorías (zona libre de ±100 kcal,
lineal a 0 en ±500) y hasta 30 por proteína (proporcional hasta el objetivo,
pasarse no resta). El % de la semana es la media de los días contados, así que
clavar el objetivo y pasarse por 240 kcal ya no valen lo mismo.
"""
from datetime import date, timedelta

from app.services.duel_service import (
    HIT_SCORE,
    PERFECT_SCORE,
    _week_result,
    day_score,
    kcal_points,
    protein_points,
)


def test_kcal_points_symmetric_and_linear():
    assert kcal_points(0) == 70
    assert kcal_points(100) == 70          # borde de la zona libre
    assert kcal_points(-100) == 70
    assert kcal_points(300) == kcal_points(-300) == 35   # mitad del tramo
    assert kcal_points(500) == 0
    assert kcal_points(900) == 0


def test_protein_points_cap_at_goal():
    assert protein_points(162, 162) == 30
    assert protein_points(200, 162) == 30   # pasarse no penaliza
    assert protein_points(81, 162) == 15
    assert protein_points(0, 162) == 0
    assert protein_points(0, None) == 30    # sin objetivo: no se puede fallar


def test_day_score_examples_from_the_mockup():
    # Jueves del boceto: +430 kcal, 135/162 g → 12 + 25 = 37
    assert day_score(2430, 135, 2000, 162) == (37, 12, 25)
    # Calorías clavadas pero 60 g de proteína → ya no es un 100
    assert day_score(2000, 60, 2000, 162) == (81, 70, 11)
    # Sin objetivo de kcal: registrar ya es cumplir
    assert day_score(1500, 40, None, None) == (100, 70, 30)


def _week(kcal_by_day, protein_by_day, today_idx=6, cheat=(), burned=None, mode="off"):
    ws = date(2026, 9, 14)  # lunes
    kcal = {ws + timedelta(days=i): v for i, v in kcal_by_day.items()}
    prot = {ws + timedelta(days=i): v for i, v in protein_by_day.items()}
    burn = {ws + timedelta(days=i): v for i, v in (burned or {}).items()}
    cheats = {ws + timedelta(days=i) for i in cheat}
    return _week_result(ws, ws + timedelta(days=today_idx), kcal, prot, burn, cheats, 2000, 160, mode)


def test_week_is_the_mean_of_counted_days():
    # L clavado (100), M -200 kcal y proteína ok (52+30=82), X sin registrar (0),
    # J comodín, V +300 y media proteína (35+15=50), S futuro, D... hoy = sábado.
    w = _week(
        {0: 2000, 1: 1800, 4: 2300},
        {0: 160, 1: 160, 4: 80},
        today_idx=5,
        cheat=(3,),
    )
    assert w.states == ["perfect", "hit", "empty", "joker", "hit", "today", "empty"]
    assert w.scores == [100, 82, 0, None, 50, None, None]
    assert w.counted == 4
    assert w.hits == 3
    assert w.pct == round((100 + 82 + 0 + 50) / 4)
    assert w.details[0].kcal_pts == 70 and w.details[0].protein_pts == 30
    assert w.details[2] is None  # nada que desglosar
    assert w.details[4].kcal_goal == 2000


def test_states_follow_the_score_thresholds():
    w = _week({0: 2000, 1: 2450}, {0: 130, 1: 0}, today_idx=2)
    # L: 70 + 24 = 94 → perfect; M: 9 + 0 = 9 → miss
    assert w.scores[0] >= PERFECT_SCORE and w.states[0] == "perfect"
    assert w.scores[1] < HIT_SCORE and w.states[1] == "miss"


def test_exercise_scales_targets_like_the_frontend():
    # 'proportional': +400 kcal quemadas → objetivo 2400 kcal y 192 g proteína.
    w = _week({0: 2400}, {0: 160}, today_idx=1, burned={0: 400}, mode="proportional")
    d = w.details[0]
    assert (d.kcal_goal, d.protein_goal) == (2400, 192)
    assert d.kcal_pts == 70 and d.protein_pts == 25
    # 'performance': las kcal suben, la proteína se queda.
    w = _week({0: 2400}, {0: 160}, today_idx=1, burned={0: 400}, mode="performance")
    assert (w.details[0].kcal_goal, w.details[0].protein_goal) == (2400, 160)
    assert w.scores[0] == 100


def test_nothing_counted_yet_gives_no_pct():
    w = _week({}, {}, today_idx=0)
    assert w.pct is None and w.counted == 0
    assert w.states[0] == "today" and w.scores == [None] * 7
