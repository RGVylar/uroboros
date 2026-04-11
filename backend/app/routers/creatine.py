from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import CreatineLog, User
from app.schemas.misc import CreatineTodayOut

router = APIRouter(prefix="/creatine", tags=["creatine"])


def _today_status(db: Session, user: User, log_date: date) -> CreatineTodayOut:
    entry = db.execute(
        select(CreatineLog).where(
            CreatineLog.user_id == user.id,
            CreatineLog.logged_date == log_date,
        )
    ).scalars().first()
    return CreatineTodayOut(taken=entry is not None, logged_date=str(log_date))


@router.get("/today", response_model=CreatineTodayOut)
def get_creatine_today(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CreatineTodayOut:
    return _today_status(db, user, date.today())


@router.post("/log", response_model=CreatineTodayOut)
def log_creatine(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CreatineTodayOut:
    today = date.today()
    existing = db.execute(
        select(CreatineLog).where(
            CreatineLog.user_id == user.id,
            CreatineLog.logged_date == today,
        )
    ).scalars().first()
    if not existing:
        db.add(CreatineLog(user_id=user.id, logged_date=today))
        db.commit()
    return CreatineTodayOut(taken=True, logged_date=str(today))


@router.delete("/today", response_model=CreatineTodayOut)
def delete_creatine_today(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CreatineTodayOut:
    today = date.today()
    entry = db.execute(
        select(CreatineLog).where(
            CreatineLog.user_id == user.id,
            CreatineLog.logged_date == today,
        )
    ).scalars().first()
    if entry:
        db.delete(entry)
        db.commit()
    return CreatineTodayOut(taken=False, logged_date=str(today))
