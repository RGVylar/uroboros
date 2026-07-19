"""Precompute everyone's current-week adherence for the anonymous percentile.

Runs from the scheduler a few times a day. Cost per run is ~3 indexed queries
per user who logged something this week — negligible — and it keeps the
percentile endpoint down to a couple of row reads instead of computing the
whole population per view (which would grow linearly with users).
"""
import logging
from datetime import datetime, time, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.diary import DiaryEntry
from app.models.weekly_adherence import WeeklyAdherence
from app.services.duel_service import current_week, week_start_for

logger = logging.getLogger(__name__)

# Distinct from the notification job's lock so they never block each other.
_ADVISORY_LOCK_ID = 7_654_322


def _try_lock(db: Session) -> bool | None:
    """Postgres: take the advisory lock (False = another worker has it).
    SQLite (demo, single process): no locking needed — return None."""
    if db.get_bind().dialect.name != "postgresql":
        return None
    return bool(db.scalar(text(f"SELECT pg_try_advisory_lock({_ADVISORY_LOCK_ID})")))


def upsert_snapshot(db: Session, user_id: int, today) -> tuple[WeeklyAdherence | None, bool]:
    """Compute and store this user's current-week adherence.

    Returns (row, changed). row is None if nothing counted yet this week.
    `changed` is False when the freshly computed value matches what's already
    stored — lets callers skip the write/commit entirely (the percentile
    endpoint calls this on every view; the scheduler already refreshes this
    snapshot several times a day, so most live recomputes are no-ops)."""
    result = current_week(db, user_id, today)
    if result.pct is None:
        return None, False
    ws = week_start_for(today)
    row = db.scalar(
        select(WeeklyAdherence).where(
            WeeklyAdherence.user_id == user_id, WeeklyAdherence.week_start == ws
        )
    )
    if row:
        changed = row.pct != result.pct or row.counted != result.counted
        if changed:
            # Only touch the attributes when they actually differ — assigning
            # even an identical value marks the row dirty, which would flush
            # an UPDATE on the next autoflush regardless of whether the
            # caller commits.
            row.pct = result.pct
            row.counted = result.counted
    else:
        row = WeeklyAdherence(user_id=user_id, week_start=ws, pct=result.pct, counted=result.counted)
        db.add(row)
        changed = True
    return row, changed


def snapshot_weekly_adherence() -> None:
    """Scheduler job: refresh the snapshot for every user active this week."""
    db: Session = SessionLocal()
    locked = False
    try:
        lock = _try_lock(db)
        if lock is False:
            return
        locked = lock is True

        today = datetime.now(timezone.utc).date()
        ws = week_start_for(today)
        ws_dt = datetime.combine(ws, time.min, tzinfo=timezone.utc)
        # Only users who logged something this week enter the ranking; the rest
        # would all sit at 0% and drown the percentile in inactive accounts.
        active_ids = list(db.scalars(
            select(DiaryEntry.user_id)
            .where(DiaryEntry.consumed_at >= ws_dt)
            .distinct()
        ))
        for uid in active_ids:
            upsert_snapshot(db, uid, today)
        db.commit()  # scheduler always commits: it's a batch pass, not a per-view write
        logger.info("Adherence snapshot refreshed for %d active users", len(active_ids))
    except Exception as e:
        logger.error("Adherence snapshot error: %s", e)
        db.rollback()
    finally:
        if locked:
            db.scalar(text(f"SELECT pg_advisory_unlock({_ADVISORY_LOCK_ID})"))
        db.close()
