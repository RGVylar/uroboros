from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import BodyMeasurementLog, User
from app.schemas.misc import BodyMeasurementIn, BodyMeasurementOut

router = APIRouter(prefix="/measurements", tags=["measurements"])


@router.get("", response_model=list[BodyMeasurementOut])
def list_measurements(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BodyMeasurementLog]:
    stmt = (
        select(BodyMeasurementLog)
        .where(BodyMeasurementLog.user_id == user.id)
        .order_by(BodyMeasurementLog.logged_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


@router.post("", response_model=BodyMeasurementOut, status_code=status.HTTP_201_CREATED)
def add_measurement(
    payload: BodyMeasurementIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BodyMeasurementLog:
    log = BodyMeasurementLog(
        user_id=user.id,
        measurements=payload.measurements,
        logged_at=payload.logged_at,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_measurement(
    log_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    log = db.get(BodyMeasurementLog, log_id)
    if not log or log.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    db.delete(log)
    db.commit()
