from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Allowed values
LocationLiteral = Literal["pantry", "fridge", "freezer"]
UnitLiteral = Literal["g", "ml", "unit"]
LogTypeLiteral = Literal["purchase", "consume", "adjust"]


# ── Inventory ────────────────────────────────────────────────────────────────

class InventoryItemIn(BaseModel):
    product_id: int
    # Quantity as user enters it (in `unit`). Kept ≥ 0.
    quantity_base: float = Field(ge=0)
    unit: UnitLiteral = "g"
    location: LocationLiteral = "pantry"
    price_per_100g: float | None = Field(default=None, ge=0)


class InventoryItemUpdate(BaseModel):
    quantity_base: float | None = Field(default=None, ge=0)
    unit: UnitLiteral | None = None
    location: LocationLiteral | None = None
    price_per_100g: float | None = Field(default=None, ge=0)


class InventoryItemOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    product_name: str
    product_brand: str | None
    calories_per_100g: float
    quantity_g: float  # canonical grams
    quantity_base: float  # user-facing quantity
    unit: str
    location: str
    price_per_100g: float | None
    updated_at: datetime

    class Config:
        from_attributes = True


class CostSummaryOut(BaseModel):
    today: float | None
    this_week: float | None
    this_month: float | None


# ── Inventory operations (consume / adjust) ──────────────────────────────────

class InventoryConsumeIn(BaseModel):
    """Subtract `quantity` (in `unit`) from stock and create a 'consume' log."""

    quantity: float = Field(gt=0)
    unit: UnitLiteral = "g"
    notes: str | None = None


class InventoryAdjustIn(BaseModel):
    """Set the absolute stock to `new_quantity` (in `unit`) and log the delta."""

    new_quantity: float = Field(ge=0)
    unit: UnitLiteral = "g"
    reason: str | None = None


# ── Inventory log ────────────────────────────────────────────────────────────

class InventoryLogOut(BaseModel):
    id: int
    user_id: int
    item_id: int | None
    product_id: int | None
    product_name: str | None
    quantity_change: float
    unit: str
    quantity_base_change: float
    log_type: str
    price_per_unit: float | None
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Unit conversion ──────────────────────────────────────────────────────────

class UnitConversionOut(BaseModel):
    from_unit: str
    to_unit: str
    factor: float
    product_id: int | None

    class Config:
        from_attributes = True


# ── Shopping list ─────────────────────────────────────────────────────────────

class ShoppingListItemIn(BaseModel):
    product_id: int | None = None
    name: str | None = None
    quantity_g: float | None = Field(default=None, gt=0)
    unit: UnitLiteral = "g"

    def model_post_init(self, __context: object) -> None:
        if not self.product_id and not self.name:
            raise ValueError("Either product_id or name must be provided")


class ShoppingListItemUpdate(BaseModel):
    is_checked: bool | None = None
    quantity_g: float | None = Field(default=None, gt=0)
    unit: UnitLiteral | None = None


class ShoppingListItemOut(BaseModel):
    id: int
    user_id: int
    product_id: int | None
    product_name: str | None
    product_brand: str | None
    quantity_g: float | None
    unit: str
    is_checked: bool
    source: str
    created_at: datetime

    class Config:
        from_attributes = True
