"""Tendencia del peso, gasto real y propuesta semanal de objetivos.

**Tendencia**: el peso de un día baila ±1 kg por agua y digestión. La
tendencia es una media móvil exponencial (10 % por día, como en The Hacker's
Diet) que respeta los huecos: si no te pesas en 4 días, el siguiente pesaje
cuenta como 4 días de golpe.

**Gasto real**: lo que comes de media menos lo que dice la báscula. Si en tres
semanas comes 2.000 kcal al día y bajas 0,5 kg por semana, gastas unas
2.000 + 0,5 × 7.700 / 7 ≈ 2.550 kcal. Para el ritmo de cambio se usa la recta
de mínimos cuadrados de los pesajes (la tendencia exponencial llega con
retraso y subestimaría el cambio).

**Propuesta**: gasto real + el margen del objetivo (el mismo del onboarding:
-400 para perder, 0 mantener, +300 ganar). Se mueve como mucho 300 kcal por
semana y por debajo de 100 kcal de diferencia no se propone nada. La proteína
se queda como está, la grasa mantiene su parte de las kcal y los hidratos
absorben el resto.

Días que no cuentan: los apuntados a medias (menos de la mitad del objetivo),
que harían creer que comes menos de lo que comes.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DiaryEntry, ExerciseSession, User, UserGoals, WeightLog

KCAL_PER_KG = 7700
TREND_ALPHA = 0.1          # peso de cada día nuevo en la tendencia

WINDOW_DAYS = 21           # se mira esto hacia atrás (sin contar hoy)
MIN_SPAN_DAYS = 14         # entre el primer y el último pesaje de la ventana
MIN_WEIGHINS = 4
MIN_LOGGED_DAYS = 10
LOGGED_DAY_FRACTION = 0.5  # un día cuenta si llega a la mitad del objetivo

OBJECTIVE_DELTA = {"lose": -400, "maintain": 0, "gain": 300}
MAX_WEEKLY_CHANGE = 300
MIN_CHANGE = 100
MIN_KCAL = 1200
# Fuera de esto el cálculo dice más de los datos (días sin apuntar, báscula
# nueva) que del usuario: mejor no proponer nada.
TDEE_RANGE = (1200, 5000)


# ── Tendencia ────────────────────────────────────────────────────────────────

@dataclass
class TrendPoint:
    day: date
    weight: float
    trend: float


def weight_trend(weighins: list[tuple[date, float]]) -> list[TrendPoint]:
    """Un punto por día con pesaje (varios el mismo día se promedian)."""
    by_day: dict[date, list[float]] = defaultdict(list)
    for d, w in weighins:
        by_day[d].append(w)
    points: list[TrendPoint] = []
    for d in sorted(by_day):
        w = sum(by_day[d]) / len(by_day[d])
        if not points:
            trend = w
        else:
            prev = points[-1]
            gap = (d - prev.day).days
            alpha = 1 - (1 - TREND_ALPHA) ** gap
            trend = prev.trend + alpha * (w - prev.trend)
        points.append(TrendPoint(d, round(w, 2), round(trend, 2)))
    return points


def weekly_rate(points: list[TrendPoint], days: int = 14) -> float | None:
    """kg por semana según la tendencia en los últimos `days` días."""
    if len(points) < 2:
        return None
    last = points[-1]
    start = next((p for p in points if p.day >= last.day - timedelta(days=days)), None)
    if start is None or (last.day - start.day).days < 7:
        return None
    return round((last.trend - start.trend) / (last.day - start.day).days * 7, 2)


def slope_kg_per_day(weighins: list[tuple[date, float]]) -> float:
    """Pendiente de la recta de mínimos cuadrados (kg/día)."""
    x0 = min(d for d, _ in weighins)
    xs = [(d - x0).days for d, _ in weighins]
    ys = [w for _, w in weighins]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


# ── Gasto real y propuesta ───────────────────────────────────────────────────

@dataclass
class Macros:
    kcal: float
    protein: float
    carbs: float
    fat: float


@dataclass
class Proposal:
    # not_enough_data · unreliable · need_objective · on_track · proposal
    status: str
    weighins: int = 0
    logged_days: int = 0
    span_days: int = 0
    avg_intake: float | None = None
    kg_per_week: float | None = None
    tdee: float | None = None
    current: Macros | None = None
    proposed: Macros | None = None
    needs: dict = field(default_factory=lambda: {
        "weighins": MIN_WEIGHINS, "logged_days": MIN_LOGGED_DAYS, "span_days": MIN_SPAN_DAYS,
    })


def _round10(x: float) -> int:
    return int(round(x / 10) * 10)


def propose(
    current: Macros,
    objective: str | None,
    weighins: list[tuple[date, float]],
    intake_by_day: dict[date, float],
    avg_burned: float = 0.0,
) -> Proposal:
    """`intake_by_day`: kcal comidas por día de la ventana. `avg_burned`:
    ejercicio medio por día, que se descuenta si el objetivo ya lo suma solo
    (modo de ajuste por ejercicio encendido)."""
    logged = [k for k in intake_by_day.values() if k >= current.kcal * LOGGED_DAY_FRACTION]
    span = (max(d for d, _ in weighins) - min(d for d, _ in weighins)).days if weighins else 0
    p = Proposal(status="not_enough_data", weighins=len(weighins), logged_days=len(logged),
                 span_days=span, current=current)
    if len(weighins) < MIN_WEIGHINS or span < MIN_SPAN_DAYS or len(logged) < MIN_LOGGED_DAYS:
        return p

    slope = slope_kg_per_day(weighins)
    p.avg_intake = round(sum(logged) / len(logged))
    p.kg_per_week = round(slope * 7, 2)
    tdee = p.avg_intake - slope * KCAL_PER_KG
    p.tdee = _round10(tdee)
    if not TDEE_RANGE[0] <= tdee <= TDEE_RANGE[1]:
        p.status = "unreliable"
        return p
    if objective not in OBJECTIVE_DELTA:
        p.status = "need_objective"
        return p

    target = tdee + OBJECTIVE_DELTA[objective] - avg_burned
    change = max(-MAX_WEEKLY_CHANGE, min(MAX_WEEKLY_CHANGE, target - current.kcal))
    if abs(change) < MIN_CHANGE:
        p.status = "on_track"
        return p

    kcal = max(MIN_KCAL, _round10(current.kcal + change))
    fat_share = (current.fat * 9 / current.kcal) if current.kcal else 0.3
    fat = round(kcal * fat_share / 9)
    protein = round(current.protein)
    carbs = max(0, round((kcal - protein * 4 - fat * 9) / 4))
    p.status = "proposal"
    p.proposed = Macros(kcal=kcal, protein=protein, carbs=carbs, fat=fat)
    return p


# ── Con la base de datos ─────────────────────────────────────────────────────

def iso_week(day: date) -> str:
    y, w, _ = day.isocalendar()
    return f"{y}-W{w:02d}"


def _utc_date(dt: datetime) -> date:
    # SQLite devuelve naive (ya en UTC); Postgres, con zona.
    return dt.date() if dt.tzinfo is None else dt.astimezone(timezone.utc).date()


def user_weighins(db: Session, user_id: int, since: date) -> list[tuple[date, float]]:
    since_dt = datetime.combine(since, time.min, tzinfo=timezone.utc)
    return [
        (_utc_date(at), w)
        for at, w in db.execute(
            select(WeightLog.logged_at, WeightLog.weight)
            .where(WeightLog.user_id == user_id, WeightLog.logged_at >= since_dt)
            .order_by(WeightLog.logged_at)
        )
    ]


def weekly_proposal(db: Session, user: User, today: date) -> Proposal | None:
    """None si no tiene objetivos todavía."""
    goals = db.get(UserGoals, user.id)
    if goals is None:
        return None
    start, end = today - timedelta(days=WINDOW_DAYS), today - timedelta(days=1)
    start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end, time.max, tzinfo=timezone.utc)

    intake: dict[date, float] = defaultdict(float)
    for at, kcal in db.execute(
        select(DiaryEntry.consumed_at, DiaryEntry.calories)
        .where(DiaryEntry.user_id == user.id, DiaryEntry.consumed_at >= start_dt, DiaryEntry.consumed_at <= end_dt)
    ):
        intake[_utc_date(at)] += kcal or 0

    weighins = [(d, w) for d, w in user_weighins(db, user.id, start) if d <= end]

    avg_burned = 0.0
    if goals.macro_adjust_mode != "off":
        burned = db.scalars(
            select(ExerciseSession.total_calories)
            .where(ExerciseSession.user_id == user.id, ExerciseSession.session_date >= start, ExerciseSession.session_date <= end)
        ).all()
        avg_burned = sum(b or 0 for b in burned) / WINDOW_DAYS

    current = Macros(kcal=goals.kcal, protein=goals.protein, carbs=goals.carbs, fat=goals.fat)
    return propose(current, goals.objective, weighins, dict(intake), avg_burned)
