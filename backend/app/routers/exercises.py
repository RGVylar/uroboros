from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Exercise
from app.schemas.exercise import ExerciseIn, ExerciseOut, ExerciseUpdate
from app.deps import get_current_user

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=list[ExerciseOut])
def list_exercises(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Obtener todos los ejercicios predefinidos del usuario."""
    stmt = select(Exercise).where(Exercise.user_id == user.id).order_by(Exercise.name)
    return list(db.scalars(stmt))


@router.post("", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
def create_exercise(
    payload: ExerciseIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Crear un nuevo ejercicio predefinido."""
    exercise = Exercise(
        user_id=user.id,
        name=payload.name,
        kcal_per_unit=payload.kcal_per_unit,
        unit=payload.unit,
    )
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


@router.patch("/{exercise_id}", response_model=ExerciseOut)
def update_exercise(
    exercise_id: int,
    payload: ExerciseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Actualizar un ejercicio predefinido."""
    exercise = db.get(Exercise, exercise_id)
    if not exercise or exercise.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    if payload.name is not None:
        exercise.name = payload.name
    if payload.kcal_per_unit is not None:
        exercise.kcal_per_unit = payload.kcal_per_unit
    if payload.unit is not None:
        exercise.unit = payload.unit

    db.commit()
    db.refresh(exercise)
    return exercise


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Eliminar un ejercicio predefinido."""
    exercise = db.get(Exercise, exercise_id)
    if not exercise or exercise.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    db.delete(exercise)
    db.commit()
