from datetime import datetime

from pydantic import BaseModel, Field

from app.models.product import ProductSource


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    brand: str | None = None
    calories_per_100g: float = Field(ge=0)
    protein_per_100g: float = Field(ge=0)
    carbs_per_100g: float = Field(ge=0)
    fat_per_100g: float = Field(ge=0)


class ProductCreate(ProductBase):
    barcode: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    calories_per_100g: float | None = Field(default=None, ge=0)
    protein_per_100g: float | None = Field(default=None, ge=0)
    carbs_per_100g: float | None = Field(default=None, ge=0)
    fat_per_100g: float | None = Field(default=None, ge=0)


class ProductOut(ProductBase):
    id: int
    barcode: str | None
    source: ProductSource
    edited_by: int | None
    edited_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendedProduct(BaseModel):
    product: ProductOut
    suggested_grams: int
    estimated_calories: float
    reason: str
