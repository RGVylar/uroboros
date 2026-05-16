"""
APScheduler job that runs every 5 minutes and sends push notifications
based on each user's preferences.

Notification types:
  • breakfast / lunch / dinner  — meal reminder if that meal has no entries
  • streak                      — streak at risk (≥ min days, nothing logged today)
  • summary                     — daily summary (≥1 meal logged today)
  • water                       — water reminder (< 50% of goal)
  • milestone_N                 — streak milestone (triggered after diary POST)
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.background import BackgroundScheduler
from pywebpush import WebPushException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.diary import DiaryEntry
from app.models.goals import UserGoals
from app.models.notification_log import NotificationLog
from app.models.notification_prefs import NotificationPrefs
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.models.water import WaterLog
from app.services import push_service
from app.services.streak_service import calculate_streak, has_entry_today

logger = logging.getLogger(__name__)

MEAL_LABELS = {
    "breakfast": "el desayuno",
    "lunch": "el almuerzo",
    "dinner": "la cena",
}
MEAL_EMOJIS = {
    "breakfast": "🍳",
    "lunch": "🥗",
    "dinner": "🍽️",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _user_tz(prefs: NotificationPrefs) -> timezone:
    """Return the user's timezone, falling back to UTC on bad values."""
    tz_name = getattr(prefs, "timezone", None) or "UTC"
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError):
        return timezone.utc


def _now_local(prefs: NotificationPrefs) -> datetime:
    return datetime.now(_user_tz(prefs))


def _in_quiet_hours(prefs: NotificationPrefs) -> bool:
    """Return True if current local hour falls in the user's quiet window."""
    h = _now_local(prefs).hour
    qs, qe = prefs.quiet_start, prefs.quiet_end
    if qs > qe:  # wraps midnight, e.g. 22–8
        return h >= qs or h < qe
    return qs <= h < qe


def _already_sent_today(db: Session, user_id: int, notif_type: str) -> bool:
    today = date.today()
    return db.scalar(
        select(NotificationLog.id).where(
            NotificationLog.user_id == user_id,
            NotificationLog.notif_type == notif_type,
        ).filter(
            NotificationLog.sent_at >= datetime.combine(today, time.min, tzinfo=timezone.utc),
            NotificationLog.sent_at <= datetime.combine(today, time.max, tzinfo=timezone.utc),
        ).limit(1)
    ) is not None


def _record_sent(db: Session, user_id: int, notif_type: str) -> None:
    db.add(NotificationLog(user_id=user_id, notif_type=notif_type))
    db.commit()


def _time_matches(target_hhmm: str, prefs: NotificationPrefs, window_minutes: int = 3) -> bool:
    """True if current local time (user's timezone) is within ±window_minutes of target_hhmm."""
    now = _now_local(prefs)
    th, tm = map(int, target_hhmm.split(":"))
    target = now.replace(hour=th, minute=tm, second=0, microsecond=0)
    diff = abs((now - target).total_seconds())
    return diff <= window_minutes * 60


def _send_to_user(db: Session, user_id: int, **kwargs) -> None:
    """Send push to ALL subscriptions of a user concurrently. Remove expired ones (410)."""
    subs = db.scalars(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    ).all()
    if not subs:
        return

    expired_endpoints: list[str] = []

    def _send_one(endpoint: str, p256dh: str, auth: str) -> str | None:
        try:
            push_service.send_push(endpoint=endpoint, p256dh=p256dh, auth=auth, **kwargs)
            return None
        except WebPushException:
            return endpoint  # expired — caller will delete

    with ThreadPoolExecutor(max_workers=min(len(subs), 10)) as pool:
        futures = {
            pool.submit(_send_one, sub.endpoint, sub.p256dh, sub.auth): sub.endpoint
            for sub in subs
        }
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                expired_endpoints.append(result)

    if expired_endpoints:
        for sub in subs:
            if sub.endpoint in expired_endpoints:
                db.delete(sub)
        db.commit()


def _water_today_ml(db: Session, user_id: int) -> float:
    today = date.today()
    rows = db.scalars(
        select(WaterLog).where(
            WaterLog.user_id == user_id,
            WaterLog.logged_at >= datetime.combine(today, time.min, tzinfo=timezone.utc),
            WaterLog.logged_at <= datetime.combine(today, time.max, tzinfo=timezone.utc),
        )
    ).all()
    return sum(r.amount_ml for r in rows)


# ── Main job ──────────────────────────────────────────────────────────────────

_ADVISORY_LOCK_ID = 7_654_321  # arbitrary app-unique int


def _check_notifications() -> None:
    db: Session = SessionLocal()
    locked = False
    try:
        # Only one worker runs this job at a time across all processes
        locked = bool(db.scalar(text(f"SELECT pg_try_advisory_lock({_ADVISORY_LOCK_ID})")))
        if not locked:
            logger.debug("Notification job skipped — another worker holds the lock")
            return

        prefs_list = db.scalars(
            select(NotificationPrefs).where(NotificationPrefs.enabled == True)
        ).all()

        for prefs in prefs_list:
            user_id = prefs.user_id

            has_sub = db.scalar(
                select(PushSubscription.id)
                .where(PushSubscription.user_id == user_id)
                .limit(1)
            )
            if not has_sub:
                continue

            if _in_quiet_hours(prefs):
                continue

            _check_meal_reminders(db, prefs, user_id)
            _check_streak_alert(db, prefs, user_id)
            _check_summary(db, prefs, user_id)
            _check_water(db, prefs, user_id)

    except Exception as e:
        logger.error("Notification scheduler error: %s", e)
    finally:
        if locked:
            db.scalar(text(f"SELECT pg_advisory_unlock({_ADVISORY_LOCK_ID})"))
        db.close()


def _check_meal_reminders(db: Session, prefs: NotificationPrefs, user_id: int) -> None:
    meals = [
        ("breakfast", prefs.breakfast_on, prefs.breakfast_time),
        ("lunch", prefs.lunch_on, prefs.lunch_time),
        ("dinner", prefs.dinner_on, prefs.dinner_time),
    ]
    for meal_key, is_on, meal_time in meals:
        if not is_on:
            continue
        if not _time_matches(meal_time, prefs):
            continue
        if _already_sent_today(db, user_id, meal_key):
            continue
        # Smart check: only notify if the meal has no entries today
        if has_entry_today(db, user_id, meal_type=meal_key):
            continue
        label = MEAL_LABELS[meal_key]
        emoji = MEAL_EMOJIS[meal_key]
        _send_to_user(
            db, user_id,
            title=f"{emoji} ¿Ya registraste {label}?",
            body="Abre uroboros para añadir lo que has comido.",
            url="/add",
        )
        _record_sent(db, user_id, meal_key)


def _check_streak_alert(db: Session, prefs: NotificationPrefs, user_id: int) -> None:
    if not prefs.streak_on:
        return
    if not _time_matches(prefs.streak_time, prefs):
        return
    if _already_sent_today(db, user_id, "streak"):
        return
    # Don't send if they already logged something today
    if has_entry_today(db, user_id):
        return
    streak = calculate_streak(db, user_id)
    if streak < prefs.streak_min_days:
        return
    _send_to_user(
        db, user_id,
        title=f"🔥 ¡Tu racha de {streak} días está en peligro!",
        body="Registra algo hoy para mantener la racha.",
        url="/add",
    )
    _record_sent(db, user_id, "streak")


def _check_summary(db: Session, prefs: NotificationPrefs, user_id: int) -> None:
    if not prefs.summary_on:
        return
    if not _time_matches(prefs.summary_time, prefs):
        return
    if _already_sent_today(db, user_id, "summary"):
        return
    if not has_entry_today(db, user_id):
        return
    # Count today's calories
    today = date.today()
    entries = db.scalars(
        select(DiaryEntry).where(
            DiaryEntry.user_id == user_id,
            DiaryEntry.consumed_at >= datetime.combine(today, time.min, tzinfo=timezone.utc),
            DiaryEntry.consumed_at <= datetime.combine(today, time.max, tzinfo=timezone.utc),
        )
    ).all()
    total_kcal = sum(e.calories for e in entries)
    goals = db.scalar(select(UserGoals).where(UserGoals.user_id == user_id))
    goal_kcal = goals.kcal if goals else 2000
    pct = round(total_kcal / goal_kcal * 100) if goal_kcal else 0
    _send_to_user(
        db, user_id,
        title="📊 Resumen de hoy",
        body=f"{int(total_kcal)} kcal · {pct}% de tu objetivo de {int(goal_kcal)} kcal",
        url="/",
    )
    _record_sent(db, user_id, "summary")


def _check_water(db: Session, prefs: NotificationPrefs, user_id: int) -> None:
    if not prefs.water_on:
        return
    if not _time_matches(prefs.water_time, prefs):
        return
    if _already_sent_today(db, user_id, "water"):
        return
    goals = db.scalar(select(UserGoals).where(UserGoals.user_id == user_id))
    goal_ml = goals.water_ml if goals else 2000
    drunk_ml = _water_today_ml(db, user_id)
    if drunk_ml >= goal_ml * 0.5:
        return  # Already past 50% — no need to remind
    _send_to_user(
        db, user_id,
        title="💧 ¡Recuerda hidratarte!",
        body=f"Llevas {int(drunk_ml)} ml de {int(goal_ml)} ml hoy.",
        url="/",
    )
    _record_sent(db, user_id, "water")


def send_milestone_push(db: Session, user_id: int, milestone: int) -> None:
    """Called from the diary router right after a new streak milestone is hit."""
    notif_type = f"milestone_{milestone}"
    if _already_sent_today(db, user_id, notif_type):
        return
    # Check user has notifications enabled
    prefs = db.scalar(select(NotificationPrefs).where(NotificationPrefs.user_id == user_id))
    if not prefs or not prefs.enabled:
        return
    _send_to_user(
        db, user_id,
        title=f"🏆 ¡{milestone} días seguidos!",
        body="Llevas una racha increíble. ¡Sigue así!",
        url="/",
    )
    _record_sent(db, user_id, notif_type)


# ── Scheduler lifecycle ───────────────────────────────────────────────────────

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_check_notifications, "interval", minutes=5, id="notif_check")
    _scheduler.start()
    logger.info("Notification scheduler started (every 5 min)")


def stop_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Notification scheduler stopped")
