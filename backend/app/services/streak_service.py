"""Streak calculation logic — extracted for reuse by scheduler and router."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cheat_day import CheatDayLog
from app.models.diary import DiaryEntry
from app.models.user import User

# Days that trigger a streak milestone notification
STREAK_MILESTONES = {3, 7, 14, 30, 60, 100, 200, 365}


def _utc_date(dt: datetime) -> date:
    """Bucket a diary timestamp by UTC day. Same rule as duel_service._utc_date:
    Postgres returns tz-aware datetimes, SQLite returns naive ones that already
    hold the UTC wall-clock we stored — handle both without shifting the date.

    NB: deliberately NOT `cast(DiaryEntry.consumed_at, Date)` in SQL — on SQLite
    that CAST silently mis-parses the stored 'YYYY-MM-DD HH:MM:SS' text as a
    NUMERIC affinity value and returns just the leading digits (e.g. the column
    holding '2026-07-19 12:00:00' comes back as the integer 2026, not a date).
    Confirmed by hand against a real SQLite session; bucketing in Python avoids
    it entirely."""
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(timezone.utc).date()


def calculate_streak(db: Session, user_id: int) -> int:
    """Count consecutive days with ≥1 diary entry (or a cheat day) going back from today (UTC).

    Today is a grace day: not having logged anything *yet* today doesn't reset
    the streak — it just doesn't count until the first entry lands.

    Was a `while` loop issuing 1-2 queries PER DAY of streak (a 365-day streak
    meant ~700 queries on the hottest path in the app — every meal logged calls
    this). Now it's 2 fixed queries that pull the set of active days once, and
    the same day-by-day walk runs in memory against that set. Semantics
    (today's grace day, cheat days count as active) are unchanged."""
    today = datetime.now(timezone.utc).date()

    entry_days: set[date] = {
        _utc_date(consumed_at)
        for consumed_at in db.scalars(
            select(DiaryEntry.consumed_at).where(DiaryEntry.user_id == user_id)
        )
    }
    cheat_days: set[date] = set(
        db.scalars(select(CheatDayLog.used_date).where(CheatDayLog.user_id == user_id))
    )
    active_days = entry_days | cheat_days

    streak = 0
    day = today
    while True:
        if day not in active_days:
            if day == today:
                day -= timedelta(days=1)
                continue
            break
        streak += 1
        day -= timedelta(days=1)
    return streak


def has_entry_today(db: Session, user_id: int, meal_type: str | None = None) -> bool:
    """Return True if the user has at least one diary entry today (UTC).
    If meal_type is given, scopes to that meal only."""
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    end = datetime.combine(today, time.max, tzinfo=timezone.utc)
    q = select(DiaryEntry.id).where(
        DiaryEntry.user_id == user_id,
        DiaryEntry.consumed_at >= start,
        DiaryEntry.consumed_at <= end,
    )
    if meal_type:
        q = q.where(DiaryEntry.meal_type == meal_type)
    return db.scalar(q.limit(1)) is not None


def milestone_hit(old_streak: int, new_streak: int) -> int | None:
    """Return the milestone value if the new streak just crossed one, else None."""
    for m in sorted(STREAK_MILESTONES):
        if old_streak < m <= new_streak:
            return m
    return None
