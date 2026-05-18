from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Allowed values for `location` and `unit` (validated in router / schemas, not DB enums)
INVENTORY_LOCATIONS = ("pantry", "fridge", "freezer")
INVENTORY_UNITS = ("g", "ml", "unit")
LOG_TYPES = ("purchase", "consume", "adjust")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    # quantity_g kept for backwards compatibility / cost-summary calculations (canonical grams)
    quantity_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # quantity_base = quantity as the user entered it (in `unit`), source of truth for UI
    quantity_base: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="g")
    location: Mapped[str] = mapped_column(String(20), nullable=False, default="pantry")
    price_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_inventory_user_product"),)


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="g")
    is_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["Product | None"] = relationship(lazy="joined")  # noqa: F821


class SharedInventoryItem(Base):
    """Inventory item shared between two users in a friendship."""
    __tablename__ = "shared_inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    friendship_id: Mapped[int] = mapped_column(ForeignKey("friendships.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quantity_base: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="g")
    location: Mapped[str] = mapped_column(String(20), nullable=False, default="pantry")
    price_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    added_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (UniqueConstraint("friendship_id", "product_id", name="uq_shared_inv_friendship_product"),)


class SharedShoppingListItem(Base):
    """Shopping list item shared between two users in a friendship."""
    __tablename__ = "shared_shopping_list_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    friendship_id: Mapped[int] = mapped_column(ForeignKey("friendships.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="g")
    is_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    added_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["Product | None"] = relationship(lazy="joined")  # noqa: F821


class InventoryLog(Base):
    """Audit log for inventory changes (purchase / consume / adjust)."""

    __tablename__ = "inventory_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=True, index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )
    quantity_change: Mapped[float] = mapped_column(Float, nullable=False)
    # positive = purchase / add, negative = consume / remove
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="g")
    quantity_base_change: Mapped[float] = mapped_column(Float, nullable=False)
    # always normalised to grams for analytics
    log_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # 'purchase' | 'consume' | 'adjust'
    price_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["Product | None"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        Index("ix_inventory_logs_user_created", "user_id", "created_at"),
    )


class UnitConversion(Base):
    """
    Conversion factors between units. 1 from_unit = factor * to_unit (in grams).

    Global rows have product_id NULL. Product-specific overrides take precedence.
    """

    __tablename__ = "unit_conversions"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    to_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="g")
    factor: Mapped[float] = mapped_column(Float, nullable=False)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_unit_conversions_from_to_product", "from_unit", "to_unit", "product_id"),
    )
