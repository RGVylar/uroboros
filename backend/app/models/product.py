import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProductSource(str, enum.Enum):
    openfoodfacts = "openfoodfacts"
    manual = "manual"
    edited = "edited"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)

    calories_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    # En qué se mide: 'g', 'ml' o 'unit'. Nulo = lo decide el cliente por el
    # nombre (leche → ml). Para 'unit' los *_per_100g son "por unidad" y
    # 1 unidad ≡ 100 g internos, el mismo factor por defecto de
    # unit_conversions, así el diario y la despensa no cambian de cálculo.
    unit: Mapped[str | None] = mapped_column(String(8), nullable=True)

    ingredients_text: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    allergens: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ["milk", "gluten", ...]

    source: Mapped[ProductSource] = mapped_column(
        Enum(ProductSource, name="product_source"), nullable=False
    )
    edited_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
