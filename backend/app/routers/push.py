"""Push notification endpoints: subscribe, prefs, test."""

from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fcm_token import FcmToken
from app.models.notification_log import NotificationLog
from app.models.notification_prefs import NotificationPrefs
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.routers.auth import get_current_user
from app.services import push_service

_TEST_DAILY_LIMIT = 5

router = APIRouter(prefix="/push", tags=["push"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SubscribeIn(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str | None = None


class FcmSubscribeIn(BaseModel):
    token: str


class PrefsOut(BaseModel):
    enabled: bool
    quiet_start: int
    quiet_end: int
    breakfast_on: bool
    breakfast_time: str
    lunch_on: bool
    lunch_time: str
    dinner_on: bool
    dinner_time: str
    streak_on: bool
    streak_time: str
    streak_min_days: int
    summary_on: bool
    summary_time: str
    water_on: bool
    water_time: str
    timezone: str


class PrefsIn(BaseModel):
    enabled: bool | None = None
    quiet_start: int | None = None
    quiet_end: int | None = None
    breakfast_on: bool | None = None
    breakfast_time: str | None = None
    lunch_on: bool | None = None
    lunch_time: str | None = None
    dinner_on: bool | None = None
    dinner_time: str | None = None
    streak_on: bool | None = None
    streak_time: str | None = None
    streak_min_days: int | None = None
    summary_on: bool | None = None
    summary_time: str | None = None
    water_on: bool | None = None
    water_time: str | None = None
    timezone: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/fcm-subscribe", status_code=status.HTTP_204_NO_CONTENT)
def fcm_subscribe(
    body: FcmSubscribeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Register (or reassociate) an FCM device token for native Android push."""
    existing = db.scalar(select(FcmToken).where(FcmToken.token == body.token))
    if existing:
        existing.user_id = user.id  # re-associate if account changed
    else:
        db.add(FcmToken(user_id=user.id, token=body.token))
    db.commit()


@router.delete("/fcm-subscribe", status_code=status.HTTP_204_NO_CONTENT)
def fcm_unsubscribe(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Remove all FCM tokens for the current user."""
    tokens = db.scalars(select(FcmToken).where(FcmToken.user_id == user.id)).all()
    for tok in tokens:
        db.delete(tok)
    db.commit()


@router.get("/vapid-public-key")
def get_vapid_public_key() -> dict:
    """Return the VAPID public key for the browser to use when subscribing."""
    return {"key": push_service.vapid_public_key()}


@router.post("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
def subscribe(
    body: SubscribeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Register (or update) a Web Push subscription for this user/device."""
    existing = db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    )
    if existing:
        # Update keys in case they changed
        existing.p256dh = body.p256dh
        existing.auth = body.auth
        existing.user_id = user.id  # re-associate if device switched accounts
    else:
        db.add(PushSubscription(
            user_id=user.id,
            endpoint=body.endpoint,
            p256dh=body.p256dh,
            auth=body.auth,
            user_agent=body.user_agent,
        ))
    db.commit()


@router.delete("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Remove all push subscriptions for the current user."""
    subs = db.scalars(
        select(PushSubscription).where(PushSubscription.user_id == user.id)
    ).all()
    for sub in subs:
        db.delete(sub)
    db.commit()


@router.get("/prefs", response_model=PrefsOut)
def get_prefs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationPrefs:
    """Get notification preferences, creating defaults if not set."""
    prefs = db.scalar(
        select(NotificationPrefs).where(NotificationPrefs.user_id == user.id)
    )
    if not prefs:
        prefs = NotificationPrefs(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.put("/prefs", response_model=PrefsOut)
def update_prefs(
    body: PrefsIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationPrefs:
    """Update notification preferences (partial update — only provided fields change)."""
    prefs = db.scalar(
        select(NotificationPrefs).where(NotificationPrefs.user_id == user.id)
    )
    if not prefs:
        prefs = NotificationPrefs(user_id=user.id)
        db.add(prefs)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(prefs, field, value)

    db.commit()
    db.refresh(prefs)
    return prefs


@router.post("/test", status_code=status.HTTP_204_NO_CONTENT)
def send_test(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Send a test push notification to all of the user's subscriptions."""
    subs = db.scalars(
        select(PushSubscription).where(PushSubscription.user_id == user.id)
    ).all()

    # Rate limit: max 5 test notifications per day
    from sqlalchemy import func as sqlfunc
    today_start = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
    test_count: int = db.scalar(
        select(sqlfunc.count()).select_from(NotificationLog).where(
            NotificationLog.user_id == user.id,
            NotificationLog.notif_type == "test",
            NotificationLog.sent_at >= today_start,
        )
    ) or 0
    if test_count >= _TEST_DAILY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Límite de {_TEST_DAILY_LIMIT} notificaciones de prueba por día",
        )

    fcm_tokens = db.scalars(select(FcmToken).where(FcmToken.user_id == user.id)).all()

    if not subs and not fcm_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay suscripciones activas para este usuario",
        )

    notif_kwargs = dict(
        title="🔔 uroboros",
        body="Las notificaciones están funcionando correctamente.",
        url="/",
    )
    for sub in subs:
        push_service.send_push(endpoint=sub.endpoint, p256dh=sub.p256dh, auth=sub.auth, **notif_kwargs)
    for tok in fcm_tokens:
        push_service.send_fcm(token=tok.token, **notif_kwargs)

    db.add(NotificationLog(user_id=user.id, notif_type="test"))
    db.commit()
