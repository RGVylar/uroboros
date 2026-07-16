"""Weekly adherence duel between two friends.

Adherence = the share of days a user hits *their own* calorie target, so the
contest is fair regardless of goal size (a cut and a maintenance are comparable).

A day counts as:
  hit    logged and within ADHERENCE_TOLERANCE kcal of the effective goal
  miss   logged but out of range
  empty  no entry (counts against you)
  joker  cheat day — excluded from the divisor, neither hit nor fail
  today  the day in progress — not counted yet

Effective goal mirrors the frontend: goal + calories burned when exercise is
logged and the macro-adjust mode is on (both 'proportional' and 'performance'
add the burned calories to the kcal target).
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cheat_day import CheatDayLog
from app.models.diary import DiaryEntry
from app.models.exercise import ExerciseSession
from app.models.goals import UserGoals

ADHERENCE_TOLERANCE = 250.0  # kcal window that still counts as hitting the goal
TIE_MARGIN = 5               # final % difference below which nobody wins
PHOTO_FINISH_MARGIN = 10     # winning by less than this earns the Photo finish badge
HISTORY_WEEKS = 6            # completed weeks used for the season tally


@dataclass
class WeekResult:
    states: list[str]        # 7 entries, Monday → Sunday
    pct: int | None          # adherence %, None if no countable days yet
    hits: int
    counted: int


def week_start_for(day: date) -> date:
    """Monday of the ISO week containing `day`."""
    return day - timedelta(days=day.weekday())


def _effective_goal(goal_kcal: float | None, burned: float, mode: str) -> float | None:
    if goal_kcal is None:
        return None
    if burned > 0 and mode != "off":
        return goal_kcal + burned
    return goal_kcal


def _utc_date(dt: datetime) -> date:
    """Bucket a diary timestamp by UTC day.

    Postgres returns tz-aware datetimes; SQLite returns naive ones that already
    hold the UTC wall-clock we stored. Handle both without shifting the date."""
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(timezone.utc).date()


def _gather(db: Session, user_id: int, start: date, end: date):
    """Return (kcal_by_date, burned_by_date, cheat_dates) for [start, end]."""
    start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end, time.max, tzinfo=timezone.utc)

    kcal_by_date: dict[date, float] = defaultdict(float)
    for consumed_at, cal in db.execute(
        select(DiaryEntry.consumed_at, DiaryEntry.calories).where(
            DiaryEntry.user_id == user_id,
            DiaryEntry.consumed_at >= start_dt,
            DiaryEntry.consumed_at <= end_dt,
        )
    ):
        kcal_by_date[_utc_date(consumed_at)] += cal

    burned_by_date: dict[date, float] = {
        sd: tc
        for sd, tc in db.execute(
            select(ExerciseSession.session_date, ExerciseSession.total_calories).where(
                ExerciseSession.user_id == user_id,
                ExerciseSession.session_date >= start,
                ExerciseSession.session_date <= end,
            )
        )
    }

    cheat_dates: set[date] = set(
        db.scalars(
            select(CheatDayLog.used_date).where(
                CheatDayLog.user_id == user_id,
                CheatDayLog.used_date >= start,
                CheatDayLog.used_date <= end,
            )
        )
    )
    return kcal_by_date, burned_by_date, cheat_dates


def _week_result(
    week_start: date,
    today: date,
    kcal_by_date: dict[date, float],
    burned_by_date: dict[date, float],
    cheat_dates: set[date],
    goal_kcal: float | None,
    mode: str,
) -> WeekResult:
    states: list[str] = []
    hits = 0
    counted = 0
    for i in range(7):
        d = week_start + timedelta(days=i)
        if d > today:
            states.append("empty")  # future day, shown but not counted
            continue
        if d == today:
            states.append("today")
            continue
        if d in cheat_dates:
            states.append("joker")
            continue
        # Past, non-cheat day — counts towards adherence.
        counted += 1
        if d not in kcal_by_date:
            states.append("empty")
            continue
        eff = _effective_goal(goal_kcal, burned_by_date.get(d, 0.0), mode)
        if eff is None:
            # No goal set: reward having logged (constancy) rather than penalise.
            states.append("hit")
            hits += 1
            continue
        if abs(kcal_by_date[d] - eff) < ADHERENCE_TOLERANCE:
            states.append("hit")
            hits += 1
        else:
            states.append("miss")
    pct = round(hits / counted * 100) if counted else None
    return WeekResult(states=states, pct=pct, hits=hits, counted=counted)


def _user_goal(db: Session, user_id: int) -> tuple[float | None, str]:
    goals = db.scalar(select(UserGoals).where(UserGoals.user_id == user_id))
    if not goals:
        return None, "off"
    return goals.kcal, goals.macro_adjust_mode or "off"


def user_weeks(db: Session, user_id: int, today: date) -> tuple[WeekResult, list[WeekResult]]:
    """Return (current_week, [past weeks newest→oldest]) for a user.

    All data for the whole window is fetched once, then bucketed per week."""
    goal_kcal, mode = _user_goal(db, user_id)
    current_start = week_start_for(today)
    oldest_start = current_start - timedelta(weeks=HISTORY_WEEKS)
    kcal_by_date, burned_by_date, cheat_dates = _gather(
        db, user_id, oldest_start, current_start + timedelta(days=6)
    )

    def result_for(ws: date) -> WeekResult:
        return _week_result(ws, today, kcal_by_date, burned_by_date, cheat_dates, goal_kcal, mode)

    current = result_for(current_start)
    past = [result_for(current_start - timedelta(weeks=n)) for n in range(1, HISTORY_WEEKS + 1)]
    return current, past
