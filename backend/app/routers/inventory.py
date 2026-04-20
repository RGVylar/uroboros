from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import InventoryItem, User
from app.models.diary import DiaryEntry
from app.schemas.inventory import (
    CostSummaryOut,
    InventoryItemIn,
    InventoryItemOut,
    InventoryItemUpdate,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _to_out(item: InventoryItem) -> InventoryItemOut:
    return InventoryItemOut(
        id=item.id,
        user_id=item.user_id,
        product_id=item.product_id,
        product_name=item.product.name,
        product_brand=item.product.brand,
        calories_per_100g=item.product.calories_per_100g,
        quantity_g=item.quantity_g,
        price_per_100g=item.price_per_100g,
        updated_at=item.updated_at,
    )


@router.get("", response_model=list[InventoryItemOut])
def list_inventory(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[InventoryItemOut]:
    stmt = (
        select(InventoryItem)
        .where(InventoryItem.user_id == user.id)
        .order_by(InventoryItem.product.has())  # joined, sort by name below
    )
    items = list(db.scalars(stmt))
    items.sort(key=lambda i: i.product.name.lower())
    return [_to_out(i) for i in items]


@router.post("", response_model=InventoryItemOut, status_code=status.HTTP_201_CREATED)
def upsert_inventory(
    payload: InventoryItemIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InventoryItemOut:
    """Add a new item or update quantity/price if product already in inventory."""
    existing = db.scalar(
        select(InventoryItem).where(
            InventoryItem.user_id == user.id,
            InventoryItem.product_id == payload.product_id,
        )
    )
    if existing:
        existing.quantity_g += payload.quantity_g
        if payload.price_per_100g is not None:
            existing.price_per_100g = payload.price_per_100g
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return _to_out(existing)

    item = InventoryItem(
        user_id=user.id,
        product_id=payload.product_id,
        quantity_g=payload.quantity_g,
        price_per_100g=payload.price_per_100g,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.patch("/{item_id}", response_model=InventoryItemOut)
def update_inventory_item(
    item_id: int,
    payload: InventoryItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InventoryItemOut:
    item = db.get(InventoryItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    if payload.quantity_g is not None:
        item.quantity_g = payload.quantity_g
    if payload.price_per_100g is not None:
        item.price_per_100g = payload.price_per_100g
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    item = db.get(InventoryItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    db.delete(item)
    db.commit()


@router.get("/cost-summary", response_model=CostSummaryOut)
def cost_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CostSummaryOut:
    """
    Calculates food spend for today / this week / this month
    using diary entries × price_per_100g from the inventory.
    Only products with a known price are included.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    # Build price map: product_id → price_per_100g
    price_map: dict[int, float] = {}
    for item in db.scalars(select(InventoryItem).where(InventoryItem.user_id == user.id)):
        if item.price_per_100g is not None:
            price_map[item.product_id] = item.price_per_100g

    if not price_map:
        return CostSummaryOut(today=None, this_week=None, this_month=None)

    entries = list(
        db.scalars(
            select(DiaryEntry).where(
                DiaryEntry.user_id == user.id,
                DiaryEntry.consumed_at >= month_start,
            )
        )
    )

    def _sum(entries: list[DiaryEntry], since: datetime) -> float | None:
        total = 0.0
        found = False
        for e in entries:
            if e.consumed_at < since:
                continue
            price = price_map.get(e.product_id)
            if price is not None:
                total += (price / 100) * e.grams
                found = True
        return round(total, 2) if found else None

    return CostSummaryOut(
        today=_sum(entries, today_start),
        this_week=_sum(entries, week_start),
        this_month=_sum(entries, month_start),
    )
