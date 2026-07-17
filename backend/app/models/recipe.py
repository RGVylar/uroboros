import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RecipeScope(str, enum.Enum):
    """Who a recipe is shared with.

    Replaces the old `is_shared` boolean, which had no granularity: flipping it
    on published the recipe to *every* accepted friend at once, so there was no
    way to keep something between partners.
    """

    none = "none"
    partner = "partner"
    friends = "friends"


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    share_scope: Mapped[RecipeScope] = mapped_column(
        Enum(RecipeScope, name="recipe_scope"),
        nullable=False,
        default=RecipeScope.none,
        server_default="none",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @property
    def is_shared(self) -> bool:
        """Shared with anyone at all. Read-only compatibility shim."""
        return self.share_scope is not RecipeScope.none

    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    grams: Mapped[float] = mapped_column(Float, nullable=False)

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")
    product: Mapped["Product"] = relationship(lazy="joined")
