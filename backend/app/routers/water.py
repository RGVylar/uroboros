from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, UserGoals, WaterLog
from app.schemas.misc import WaterDayOut, WaterLogIn

router = APIRouter(prefix="/water", tags=["water"])


@router.post("/log", response_model=WaterDayOut)
def log_water(
    payload: WaterLogIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WaterDayOut:
    log_date = date.fromisoformat(payload.logged_date)
    entry = WaterLog(user_id=user.id, ml=payload.ml, logged_date=log_date)
    db.add(entry)
    db.commit()
    return _day_total(db, user, log_date)


@router.delete("/log/last")
def delete_last_water(
    day: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WaterDayOut:
    log_date = date.fromisoformat(day)
    last = (
        db.execute(
            select(WaterLog)
            .where(WaterLog.user_id == user.id, WaterLog.logged_date == log_date)
            .order_by(WaterLog.id.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if last:
        db.delete(last)
        db.commit()
    return _day_total(db, user, log_date)


@router.get("/day", response_model=WaterDayOut)
def get_water_day(
    day: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WaterDayOut:
    log_date = date.fromisoformat(day)
    return _day_total(db, user, log_date)


def _day_total(db: Session, user: User, log_date: date) -> WaterDayOut:
    total = db.execute(
        select(func.coalesce(func.sum(WaterLog.ml), 0)).where(
            WaterLog.user_id == user.id,
            WaterLog.logged_date == log_date,
        )
    ).scalar()
    goals = db.get(UserGoals, user.id)
    goal_ml = goals.water_ml if goals else 2000
    return WaterDayOut(total_ml=float(total), goal_ml=goal_ml)
