from datetime import datetime

from pydantic import BaseModel, Field


# ── Inventory ────────────────────────────────────────────────────────────────

class InventoryItemIn(BaseModel):
    product_id: int
    quantity_g: float = Field(ge=0)
    price_per_100g: float | None = Field(default=None, ge=0)


class InventoryItemUpdate(BaseModel):
    quantity_g: float | None = Field(default=None, ge=0)
    price_per_100g: float | None = Field(default=None, ge=0)


class InventoryItemOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    product_name: str
    product_brand: str | None
    calories_per_100g: float
    quantity_g: float
    price_per_100g: float | None
    updated_at: datetime

    class Config:
        from_attributes = True


class CostSummaryOut(BaseModel):
    today: float | None
    this_week: float | None
    this_month: float | None


# ── Shopping list ─────────────────────────────────────────────────────────────

class ShoppingListItemIn(BaseModel):
    product_id: int | None = None
    name: str | None = None
    quantity_g: float | None = Field(default=None, gt=0)

    def model_post_init(self, __context: object) -> None:
        if not self.product_id and not self.name:
            raise ValueError("Either product_id or name must be provided")


class ShoppingListItemUpdate(BaseModel):
    is_checked: bool | None = None
    quantity_g: float | None = Field(default=None, gt=0)


class ShoppingListItemOut(BaseModel):
    id: int
    user_id: int
    product_id: int | None
    product_name: str | None
    product_brand: str | None
    quantity_g: float | None
    is_checked: bool
    source: str
    created_at: datetime

    class Config:
        from_attributes = True
