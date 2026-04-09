from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.product import ProductOut


class DiaryEntryCreate(BaseModel):
    product_id: int
    grams: float = Field(gt=0)
    consumed_at: datetime
    # killer feature: also log this exact entry for another user
    also_for_user_id: int | None = None


class DiaryEntryOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    grams: float
    calories: float
    protein: float
    carbs: float
    fat: float
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


class DaySummary(BaseModel):
    date: str  # YYYY-MM-DD
    totals: DayTotals
    entries: list[DiaryEntryOut]
