from datetime import datetime
from pydantic import BaseModel, Field


class ExerciseIn(BaseModel):
    """Schema para crear un nuevo ejercicio."""
    name: str = Field(min_length=1, max_length=255)
    kcal_per_unit: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=50)  # "repeticiones", "minutos", "km", etc.


class ExerciseUpdate(BaseModel):
    """Schema para actualizar un ejercicio."""
    name: str | None = None
    kcal_per_unit: float | None = Field(default=None, gt=0)
    unit: str | None = None


class ExerciseOut(BaseModel):
    """Schema de respuesta para un ejercicio."""
    id: int
    user_id: int | None
    name: str
    kcal_per_unit: float
    unit: str
    is_predefined: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
