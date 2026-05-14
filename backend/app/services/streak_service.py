"""Streak calculation logic — extracted for reuse by scheduler and router."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cheat_day import CheatDayLog
from app.models.diary import DiaryEntry
from app.models.user import User

# Days that trigger a streak milestone notification
STREAK_MILESTONES = {3, 7, 14, 30, 60, 100, 200, 365}


def calculate_streak(db: Session, user_id: int) -> int:
    """Count consecutive days with ≥1 diary entry (or a cheat day) going back from today (UTC)."""
    streak = 0
    day = datetime.now(timezone.utc).date()
    while True:
        start = datetime.combine(day, time.min, tzinfo=timezone.utc)
        end = datetime.combine(day, time.max, tzinfo=timezone.utc)
        has_entry = db.scalar(
            select(DiaryEntry.id)
            .where(
                DiaryEntry.user_id == user_id,
                DiaryEntry.consumed_at >= start,
                DiaryEntry.consumed_at <= end,
            )
            .limit(1)
        )
        if not has_entry:
            is_cheat_day = db.scalar(
                select(CheatDayLog.id)
                .where(CheatDayLog.user_id == user_id, CheatDayLog.used_date == day)
            )
            if not is_cheat_day:
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
