from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from datetime import date
from app.database import get_db
from app.models import User, Exercise, ExerciseSession, ExerciseSessionEntry
from app.schemas.exercise_session import (
    ExerciseSessionOut,
    ExerciseSessionEntryIn,
    ExerciseSessionEntryUpdate,
)
from app.deps import get_current_user

router = APIRouter(prefix="/exercise-sessions", tags=["exercise-sessions"])


def _recalc_total(session: ExerciseSession) -> None:
    """Recalcular y actualizar total_calories de la sesión."""
    session.total_calories = sum(e.calories for e in session.entries)


@router.get("/day", response_model=ExerciseSessionOut | None)
def get_session_by_day(
    day: date = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Obtener sesión de ejercicio de un día específico. Devuelve null si no existe."""
    session = db.scalar(
        select(ExerciseSession).where(
            and_(ExerciseSession.user_id == user.id, ExerciseSession.session_date == day)
        )
    )
    return session


@router.post("/day/entry", response_model=ExerciseSessionOut)
def add_entry_to_session(
    payload: ExerciseSessionEntryIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Agregar un ejercicio a la sesión del día (crea la sesión si no existe)."""
    exercise = db.get(Exercise, payload.exercise_id)
    # Permitir ejercicios predefinidos (user_id == None) además de los propios del usuario
    if not exercise or (exercise.user_id is not None and exercise.user_id != user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    # Obtener o crear sesión del día
    session = db.scalar(
        select(ExerciseSession).where(
            and_(
                ExerciseSession.user_id == user.id,
                ExerciseSession.session_date == payload.date,
            )
        )
    )
    if not session:
        session = ExerciseSession(user_id=user.id, session_date=payload.date, total_calories=0)
        db.add(session)
        db.flush()

    # Si ya existe entrada para este ejercicio, actualizarla; si no, crearla
    existing = db.scalar(
        select(ExerciseSessionEntry).where(
            and_(
                ExerciseSessionEntry.session_id == session.id,
                ExerciseSessionEntry.exercise_id == payload.exercise_id,
            )
        )
    )
    if existing:
        existing.quantity = payload.quantity
        existing.calories = payload.quantity * exercise.kcal_per_unit
    else:
        entry = ExerciseSessionEntry(
            session_id=session.id,
            exercise_id=payload.exercise_id,
            quantity=payload.quantity,
            calories=payload.quantity * exercise.kcal_per_unit,
        )
        db.add(entry)
        db.flush()

    _recalc_total(session)
    db.commit()
    db.refresh(session)
    return session


@router.patch("/day/entry/{entry_id}", response_model=ExerciseSessionOut)
def update_entry_quantity(
    entry_id: int,
    payload: ExerciseSessionEntryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Actualizar la cantidad de un ejercicio en la sesión."""
    entry = db.get(ExerciseSessionEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    session = db.get(ExerciseSession, entry.session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    entry.quantity = payload.quantity
    entry.calories = payload.quantity * entry.exercise.kcal_per_unit

    _recalc_total(session)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/day/entry/{entry_id}", response_model=ExerciseSessionOut | None)
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Eliminar un ejercicio de la sesión. Si queda vacía, elimina la sesión."""
    entry = db.get(ExerciseSessionEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    session = db.get(ExerciseSession, entry.session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    db.delete(entry)
    db.flush()

    if not session.entries:
        db.delete(session)
        db.commit()
        return None

    _recalc_total(session)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/day", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    day: date = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Eliminar toda la sesión de ejercicio de un día."""
    session = db.scalar(
        select(ExerciseSession).where(
            and_(ExerciseSession.user_id == user.id, ExerciseSession.session_date == day)
        )
    )
    if session:
        db.delete(session)
        db.commit()
