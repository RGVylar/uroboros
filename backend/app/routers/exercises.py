from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Exercise
from app.schemas.exercise import ExerciseIn, ExerciseOut, ExerciseUpdate
from app.deps import get_current_user

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=list[ExerciseOut])
def list_exercises(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Ejercicios del usuario + predefinidos globales."""
    stmt = (
        select(Exercise)
        .where(or_(Exercise.user_id == user.id, Exercise.is_predefined == True))  # noqa: E712
        .order_by(Exercise.is_predefined.desc(), Exercise.name)
    )
    return list(db.scalars(stmt))


@router.post("", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
def create_exercise(
    payload: ExerciseIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    exercise = Exercise(
        user_id=user.id,
        name=payload.name,
        kcal_per_unit=payload.kcal_per_unit,
        unit=payload.unit,
        is_predefined=False,
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
    exercise = db.get(Exercise, exercise_id)
    if not exercise or exercise.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    if exercise.is_predefined:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit predefined exercise")

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
    exercise = db.get(Exercise, exercise_id)
    if not exercise or exercise.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    if exercise.is_predefined:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete predefined exercise")

    db.delete(exercise)
    db.commit()
