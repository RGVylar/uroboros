import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MealType(str, enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class DiaryEntry(Base):
    """A logged consumption. Macros are snapshotted at log time so later
    product edits do NOT rewrite history."""

    __tablename__ = "diary_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)

    grams: Mapped[float] = mapped_column(Float, nullable=False)
    meal_type: Mapped[MealType] = mapped_column(
        Enum(MealType, name="meal_type"), nullable=False, server_default="snack"
    )

    # snapshot of macros at the moment of logging (already scaled to `grams`)
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, nullable=False)
    fat: Mapped[float] = mapped_column(Float, nullable=False)

    consumed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    recipe_id: Mapped[int | None] = mapped_column(
        ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Ración sacada de una olla. Lo que queda en la olla se calcula con estas
    # entradas: borrarla devuelve su parte.
    pot_id: Mapped[int | None] = mapped_column(
        ForeignKey("pots.id", ondelete="SET NULL"), nullable=True, index=True
    )

    product: Mapped["Product"] = relationship(lazy="joined")  # noqa: F821
    # Solo para el nombre: el diario agrupa bajo "Pollo con arroz" lo que se
    # registró como receta, en vez de dejar sus ingredientes sueltos.
    recipe: Mapped["Recipe | None"] = relationship(lazy="selectin")  # noqa: F821

    @property
    def recipe_name(self) -> str | None:
        return self.recipe.name if self.recipe is not None else None

    __table_args__ = (
        Index("ix_diary_entries_user_consumed", "user_id", "consumed_at"),
    )
