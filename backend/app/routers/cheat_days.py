from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.cheat_day import CheatDayLog
from app.models.user import User
from pydantic import BaseModel

router = APIRouter(prefix="/cheat-days", tags=["cheat-days"])


class CheatDayOut(BaseModel):
    active: bool
    used_date: str  # YYYY-MM-DD


def _today_status(db: Session, user: User, log_date: date) -> CheatDayOut:
    entry = db.scalar(
        select(CheatDayLog).where(
            CheatDayLog.user_id == user.id,
            CheatDayLog.used_date == log_date,
        )
    )
    return CheatDayOut(active=entry is not None, used_date=str(log_date))


@router.get("/today", response_model=CheatDayOut)
def get_cheat_day_today(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CheatDayOut:
    return _today_status(db, user, date.today())


@router.post("/use", response_model=CheatDayOut)
def use_cheat_day(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CheatDayOut:
    today = date.today()
    existing = db.scalar(
        select(CheatDayLog).where(
            CheatDayLog.user_id == user.id,
            CheatDayLog.used_date == today,
        )
    )
    if not existing:
        db.add(CheatDayLog(user_id=user.id, used_date=today))
        db.commit()
    return CheatDayOut(active=True, used_date=str(today))


@router.delete("/today", response_model=CheatDayOut)
def cancel_cheat_day(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CheatDayOut:
    today = date.today()
    entry = db.scalar(
        select(CheatDayLog).where(
            CheatDayLog.user_id == user.id,
            CheatDayLog.used_date == today,
        )
    )
    if entry:
        db.delete(entry)
        db.commit()
    return CheatDayOut(active=False, used_date=str(today))
