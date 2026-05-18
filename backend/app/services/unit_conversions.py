"""Unit conversion service.

Resolves the factor needed to convert a quantity expressed in some `unit`
(g | ml | unit) to canonical grams. Looks up `UnitConversion` rows:

    1. Product-specific row (highest priority).
    2. Global row (product_id IS NULL).
    3. Hard-coded fallback (so the API never explodes if the table is empty).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import UnitConversion


# Fallback values used when no DB row exists. Conservative defaults.
_FALLBACK: dict[tuple[str, str], float] = {
    ("g", "g"): 1.0,
    ("ml", "g"): 1.0,
    ("unit", "g"): 100.0,  # generic 1 unit ≈ 100 g; can be overridden per product
}


def get_conversion_factor(
    db: Session,
    from_unit: str,
    to_unit: str = "g",
    product_id: int | None = None,
) -> float:
    """Return the multiplicative factor: 1 `from_unit` = factor * `to_unit`.

    Falls back to a sensible default if no row exists.
    """
    if from_unit == to_unit:
        return 1.0

    # 1. Product-specific override
    if product_id is not None:
        row = db.scalar(
            select(UnitConversion).where(
                UnitConversion.from_unit == from_unit,
                UnitConversion.to_unit == to_unit,
                UnitConversion.product_id == product_id,
            )
        )
        if row:
            return row.factor

    # 2. Global row
    row = db.scalar(
        select(UnitConversion).where(
            UnitConversion.from_unit == from_unit,
            UnitConversion.to_unit == to_unit,
            UnitConversion.product_id.is_(None),
        )
    )
    if row:
        return row.factor

    # 3. Hard-coded fallback
    return _FALLBACK.get((from_unit, to_unit), 1.0)


def to_grams(
    db: Session,
    quantity: float,
    unit: str,
    product_id: int | None = None,
) -> float:
    """Convenience: convert `quantity` of `unit` to grams."""
    factor = get_conversion_factor(db, unit, "g", product_id)
    return quantity * factor
