from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.diary import MealTypeLiteral


class PotIngredientIn(BaseModel):
    product_id: int
    grams: float = Field(gt=0)


class PotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    servings: float = Field(gt=0, le=100)
    cooked_weight: float | None = Field(default=None, gt=0)
    # Compartirla con la pareja (si la hay): los dos apuntan de ella.
    shared: bool = True
    # Ingredientes a mano, o los de una receta (se copian, no se enlazan).
    ingredients: list[PotIngredientIn] | None = None
    recipe_id: int | None = None

    @model_validator(mode="after")
    def _one_source(self) -> "PotCreate":
        if not self.ingredients and self.recipe_id is None:
            raise ValueError("ingredients or recipe_id required")
        return self


class PotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    servings: float | None = Field(default=None, gt=0, le=100)
    # Peso de la comida cocinada que hay en la olla AHORA. Si ya se ha comido
    # algo, el servidor deduce el total con lo que queda.
    weight_now: float | None = Field(default=None, gt=0)
    # Quitar el peso y volver a raciones.
    clear_weight: bool = False


class PotLogIn(BaseModel):
    """Una ración de la olla al diario. O raciones, o gramos (si está pesada)."""

    servings: float | None = Field(default=None, gt=0)
    grams: float | None = Field(default=None, gt=0)
    # Acabarse lo que queda, se haya pesado o no.
    rest: bool = False
    meal_type: MealTypeLiteral
    consumed_at: datetime
    also_for_user_id: int | None = None
    only_for_user_id: int | None = None

    @model_validator(mode="after")
    def _one_amount(self) -> "PotLogIn":
        if (self.servings is not None) + (self.grams is not None) + self.rest != 1:
            raise ValueError("servings, grams or rest: exactly one")
        return self


class PotIngredientOut(BaseModel):
    id: int
    product_id: int
    name: str
    grams: float


class PotEaten(BaseModel):
    user_id: int
    servings: float


class PotDay(BaseModel):
    day: date
    user_id: int
    servings: float


class PotOut(BaseModel):
    id: int
    name: str
    owner_id: int
    partner_id: int | None
    servings: float
    cooked_weight: float | None
    raw_weight: float
    created_at: datetime
    finished_at: datetime | None
    # Macros de la olla entera (suma de ingredientes en crudo).
    calories: float
    protein: float
    carbs: float
    fat: float
    ingredients: list[PotIngredientOut]
    eaten: list[PotEaten]
    days: list[PotDay]
    remaining: float  # raciones
