from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.diary import MealType
from app.schemas.product import ProductOut

MealTypeLiteral = Literal["breakfast", "lunch", "dinner", "snack"]

MEAL_LABELS = {
    "breakfast": "Desayuno",
    "lunch": "Almuerzo",
    "dinner": "Cena",
    "snack": "Snack",
}

MEAL_ORDER = ["breakfast", "lunch", "dinner", "snack"]


class DiaryEntryCreate(BaseModel):
    product_id: int
    grams: float = Field(gt=0)
    consumed_at: datetime
    meal_type: MealTypeLiteral = "snack"
    also_for_user_id: int | None = None


class DiaryEntryUpdate(BaseModel):
    grams: float = Field(gt=0)
    meal_type: MealTypeLiteral | None = None


class DiaryEntryOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    grams: float
    calories: float
    protein: float
    carbs: float
    fat: float
    meal_type: MealTypeLiteral = "snack"
    consumed_at: datetime
    created_at: datetime
    product: ProductOut | None = None

    class Config:
        from_attributes = True


class DayTotals(BaseModel):
    calories: float
    protein: float
    carbs: float
    fat: float


class MealSection(BaseModel):
    meal_type: MealTypeLiteral
    label: str
    totals: DayTotals
    entries: list[DiaryEntryOut]


class DaySummary(BaseModel):
    date: str  # YYYY-MM-DD
    totals: DayTotals
    meals: list[MealSection]
    entries: list[DiaryEntryOut]
