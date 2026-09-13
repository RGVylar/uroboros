from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_premium
from app.models.cheat_day import CheatDayLog
from app.models.goals import UserGoals
from app.models.user import User
from pydantic import BaseModel

router = APIRouter(prefix="/cheat-days", tags=["cheat-days"])

# Semana de lunes a domingo, la misma que el duelo y la adherencia semanal.
# Ver duel_service.week_start_for; se repite aquí para no arrastrar ese módulo.
def _week_bounds(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


class CheatDayOut(BaseModel):
    active: bool
    used_date: str  # YYYY-MM-DD
    # Cuántos van esta semana y cuántos permite el usuario, para que la app
    # pueda enseñar "1/1" y apagar el botón sin esperar al 409.
    used_this_week: int
    limit_per_week: int


def _used_this_week(db: Session, user_id: int, day: date) -> int:
    start, end = _week_bounds(day)
    return db.scalar(
        select(func.count()).select_from(CheatDayLog).where(
            CheatDayLog.user_id == user_id,
            CheatDayLog.used_date >= start,
            CheatDayLog.used_date <= end,
        )
    ) or 0


def _limit(db: Session, user_id: int) -> int:
    goals = db.get(UserGoals, user_id)
    return goals.cheat_days_per_week if goals else 1


def _status(db: Session, user: User, day: date) -> CheatDayOut:
    entry = db.scalar(
        select(CheatDayLog).where(
            CheatDayLog.user_id == user.id,
            CheatDayLog.used_date == day,
        )
    )
    return CheatDayOut(
        active=entry is not None,
        used_date=str(day),
        used_this_week=_used_this_week(db, user.id, day),
        limit_per_week=_limit(db, user.id),
    )


@router.get("/today", response_model=CheatDayOut)
def get_cheat_day_today(
    db: Session = Depends(get_db),
    user: User = Depends(require_premium),
) -> CheatDayOut:
    return _status(db, user, date.today())


@router.post("/use", response_model=CheatDayOut)
def use_cheat_day(
    db: Session = Depends(get_db),
    user: User = Depends(require_premium),
) -> CheatDayOut:
    today = date.today()
    existing = db.scalar(
        select(CheatDayLog).where(
            CheatDayLog.user_id == user.id,
            CheatDayLog.used_date == today,
        )
    )
    if not existing:
        # Activar otra vez el de hoy es idempotente; lo que se limita es
        # gastar uno *nuevo* cuando la semana ya está al tope.
        if _used_this_week(db, user.id, today) >= _limit(db, user.id):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="cheat_day_limit_reached")
        db.add(CheatDayLog(user_id=user.id, used_date=today))
        db.commit()
    return _status(db, user, today)


@router.delete("/today", response_model=CheatDayOut)
def cancel_cheat_day(
    db: Session = Depends(get_db),
    user: User = Depends(require_premium),
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
    return _status(db, user, today)


@router.get("/month", response_model=list[str])
def get_cheat_days_month(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_premium),
) -> list[str]:
    """Returns list of YYYY-MM-DD strings where cheat day was used in the given month."""
    rows = db.execute(
        select(CheatDayLog.used_date).where(
            CheatDayLog.user_id == user.id,
            extract("year", CheatDayLog.used_date) == year,
            extract("month", CheatDayLog.used_date) == month,
        )
    ).scalars().all()
    return [str(d) for d in rows]
