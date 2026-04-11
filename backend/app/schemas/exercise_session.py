from datetime import datetime, date
from pydantic import BaseModel, Field
from app.schemas.exercise import ExerciseOut


class ExerciseSessionEntryIn(BaseModel):
    """Schema para agregar un ejercicio a la sesión del día."""
    date: date
    exercise_id: int
    quantity: float = Field(gt=0)


class ExerciseSessionEntryUpdate(BaseModel):
    """Schema para actualizar la cantidad de un ejercicio."""
    quantity: float = Field(gt=0)


class ExerciseSessionEntryOut(BaseModel):
    """Schema de respuesta para una entrada de la sesión."""
    id: int
    session_id: int
    exercise_id: int
    quantity: float
    calories: float
    created_at: datetime
    exercise: ExerciseOut | None = None

    class Config:
        from_attributes = True


class ExerciseSessionOut(BaseModel):
    """Schema de respuesta para una sesión de ejercicio."""
    id: int
    user_id: int
    session_date: date
    total_calories: float
    entries: list[ExerciseSessionEntryOut] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
