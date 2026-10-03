from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import DailySteps, User
from app.schemas.misc import StepsDayOut, StepsSyncIn

router = APIRouter(prefix="/steps", tags=["steps"])

# Lo que se puede pedir de una vez: de sobra para una gráfica mensual.
MAX_RANGE_DAYS = 366


@router.put("", response_model=list[StepsDayOut])
def sync_steps(
    payload: StepsSyncIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DailySteps]:
    """Guarda los totales diarios que manda el móvil. Idempotente: reenviar
    los mismos días solo los sobrescribe, así que el cliente puede mandar
    siempre la última semana sin llevar la cuenta de qué subió ya."""
    by_day = {d.day: d for d in payload.days}  # si un día viene repetido, gana el último
    existing = {
        row.day: row
        for row in db.scalars(
            select(DailySteps).where(DailySteps.user_id == user.id, DailySteps.day.in_(by_day))
        )
    }
    rows = []
    for day, item in sorted(by_day.items()):
        row = existing.get(day)
        if row is None:
            row = DailySteps(user_id=user.id, day=day, steps=item.steps, source=payload.source)
            db.add(row)
        else:
            row.steps = item.steps
            row.source = payload.source
        rows.append(row)
    db.commit()
    return rows


@router.get("", response_model=list[StepsDayOut])
def list_steps(
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DailySteps]:
    """Días con pasos en [start, end], ambos incluidos. Los días sin dato no
    salen: "no hay lectura" no es lo mismo que "0 pasos"."""
    if end < start or (end - start).days > MAX_RANGE_DAYS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_range")
    stmt = (
        select(DailySteps)
        .where(DailySteps.user_id == user.id, DailySteps.day >= start, DailySteps.day <= end)
        .order_by(DailySteps.day)
    )
    return list(db.scalars(stmt))
