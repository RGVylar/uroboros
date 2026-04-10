from datetime import datetime

from pydantic import BaseModel, Field


class GoalsIn(BaseModel):
    kcal: float = Field(ge=0)
    protein: float = Field(ge=0)
    carbs: float = Field(ge=0)
    fat: float = Field(ge=0)
    water_ml: float = Field(ge=0, default=2000)


class GoalsOut(GoalsIn):
    user_id: int

    class Config:
        from_attributes = True


class WaterLogIn(BaseModel):
    ml: float = Field(gt=0)
    logged_date: str  # YYYY-MM-DD


class WaterDayOut(BaseModel):
    total_ml: float
    goal_ml: float


class WeightIn(BaseModel):
    weight: float = Field(gt=0)
    logged_at: datetime


class WeightOut(BaseModel):
    id: int
    user_id: int
    weight: float
    logged_at: datetime

    class Config:
        from_attributes = True


class RecipeIngredientIn(BaseModel):
    product_id: int
    grams: float = Field(gt=0)


class RecipeIngredientOut(RecipeIngredientIn):
    id: int

    class Config:
        from_attributes = True


class RecipeIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    ingredients: list[RecipeIngredientIn]


class RecipeOut(BaseModel):
    id: int
    name: str
    owner_id: int
    ingredients: list[RecipeIngredientOut]

    class Config:
        from_attributes = True
