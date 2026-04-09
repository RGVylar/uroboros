from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, WeightLog
from app.schemas.misc import WeightIn, WeightOut

router = APIRouter(prefix="/weight", tags=["weight"])


@router.get("", response_model=list[WeightOut])
def list_weights(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[WeightLog]:
    stmt = (
        select(WeightLog)
        .where(WeightLog.user_id == user.id)
        .order_by(WeightLog.logged_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


@router.post("", response_model=WeightOut, status_code=status.HTTP_201_CREATED)
def add_weight(
    payload: WeightIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WeightLog:
    log = WeightLog(user_id=user.id, weight=payload.weight, logged_at=payload.logged_at)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weight(
    log_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    log = db.get(WeightLog, log_id)
    if not log or log.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    db.delete(log)
    db.commit()
