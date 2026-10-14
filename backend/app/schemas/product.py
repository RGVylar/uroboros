from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, model_validator

ProductUnit = Literal["g", "ml", "unit"]

from app.models.product import ProductSource


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    brand: str | None = None
    calories_per_100g: float = Field(ge=0)
    protein_per_100g: float = Field(ge=0)
    carbs_per_100g: float = Field(ge=0)
    fat_per_100g: float = Field(ge=0)
    unit: ProductUnit | None = None


class ProductCreate(ProductBase):
    barcode: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    calories_per_100g: float | None = Field(default=None, ge=0)
    protein_per_100g: float | None = Field(default=None, ge=0)
    carbs_per_100g: float | None = Field(default=None, ge=0)
    fat_per_100g: float | None = Field(default=None, ge=0)
    unit: ProductUnit | None = None

    @model_validator(mode="after")
    def _no_null_required(self) -> "ProductUpdate":
        # Omitir un campo = no tocarlo; mandarlo a null en uno NOT NULL
        # reventaba con IntegrityError (un input numérico vaciado llega null).
        for field in ("name", "calories_per_100g", "protein_per_100g", "carbs_per_100g", "fat_per_100g"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ProductOut(ProductBase):
    # De un Product se lee display_name (traducido si es un genérico); de un
    # dict, name a secas.
    name: str = Field(validation_alias=AliasChoices("display_name", "name"))
    id: int
    barcode: str | None
    source: ProductSource
    edited_by: int | None
    edited_at: datetime | None
    created_at: datetime
    ingredients_text: str | None = None
    allergens: list[str] | None = None
    package_qty: float | None = None
    serving_qty: float | None = None

    class Config:
        from_attributes = True


class RecommendedProduct(BaseModel):
    product: ProductOut
    suggested_grams: int
    estimated_calories: float
    # El motivo va estructurado, no como frase: el cliente lo redacta en su
    # idioma. reason_kind es "freq" (comido N veces) o "macro" (X g por 100 g).
    reason_kind: str
    reason_freq: int
    reason_macro_per_100g: float | None = None


class FrequentProduct(BaseModel):
    product: ProductOut
    count: int
