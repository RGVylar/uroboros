from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.measurement_keys import MEASUREMENT_KEYS


class GoalsIn(BaseModel):
    kcal: float = Field(ge=0)
    protein: float = Field(ge=0)
    carbs: float = Field(ge=0)
    fat: float = Field(ge=0)
    water_ml: float = Field(ge=0, default=2000)
    track_creatine: bool = False
    cheat_days_enabled: bool = False
    inventory_enabled: bool = False


class GoalsOut(GoalsIn):
    user_id: int

    class Config:
        from_attributes = True


class CreatineTodayOut(BaseModel):
    taken: bool
    logged_date: str  # YYYY-MM-DD


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


class BodyMeasurementIn(BaseModel):
    measurements: dict[str, float]
    logged_at: datetime

    @field_validator("measurements")
    @classmethod
    def validate_measurements(cls, v: dict[str, float]) -> dict[str, float]:
        if not v:
            raise ValueError("At least one measurement is required")
        out: dict[str, float] = {}
        for key, val in v.items():
            if key not in MEASUREMENT_KEYS:
                raise ValueError(f"Unknown measurement key: {key}")
            if val <= 0:
                raise ValueError("Measurement values must be positive")
            out[key] = val
        return out


class BodyMeasurementOut(BaseModel):
    id: int
    user_id: int
    measurements: dict[str, float]
    logged_at: datetime

    class Config:
        from_attributes = True


class RecipeIngredientIn(BaseModel):
    product_id: int
    grams: float = Field(gt=0)


class RecipeIngredientOut(BaseModel):
    id: int
    product_id: int
    grams: float
    product: "ProductOutMinimal"

    class Config:
        from_attributes = True


class RecipeIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    ingredients: list[RecipeIngredientIn]
    is_shared: bool = False


class RecipeOut(BaseModel):
    id: int
    name: str
    owner_id: int
    is_shared: bool
    ingredients: list[RecipeIngredientOut]

    class Config:
        from_attributes = True


class SharedRecipeOut(RecipeOut):
    owner_name: str


class ProductOutMinimal(BaseModel):
    id: int
    name: str
    brand: str | None
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float

    class Config:
        from_attributes = True


RecipeIngredientOut.model_rebuild()
