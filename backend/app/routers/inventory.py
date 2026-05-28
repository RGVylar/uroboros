from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import (
    InventoryItem,
    InventoryLog,
    SharedInventoryItem,
    UnitConversion,
    User,
)
from app.models.diary import DiaryEntry
from app.models.friendship import Friendship, FriendshipStatus
from app.schemas.inventory import (
    CostSummaryOut,
    InventoryAdjustIn,
    InventoryConsumeIn,
    InventoryItemIn,
    InventoryItemOut,
    InventoryItemUpdate,
    InventoryLogOut,
    UnitConversionOut,
)
from app.services.unit_conversions import get_conversion_factor, to_grams

router = APIRouter(prefix="/inventory", tags=["inventory"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_active_shared_friendship(db: Session, user_id: int) -> Friendship | None:
    """Return the accepted friendship with shared_inventory=True for this user, if any."""
    return db.scalar(
        select(Friendship).where(
            or_(Friendship.requester_id == user_id, Friendship.receiver_id == user_id),
            Friendship.status == FriendshipStatus.accepted,
            Friendship.shared_inventory_requester == True,  # noqa: E712
            Friendship.shared_inventory_receiver == True,  # noqa: E712
        )
    )


def _to_out_personal(item: InventoryItem) -> InventoryItemOut:
    return InventoryItemOut(
        id=item.id,
        user_id=item.user_id,
        product_id=item.product_id,
        product_name=item.product.name,
        product_brand=item.product.brand,
        calories_per_100g=item.product.calories_per_100g,
        quantity_g=item.quantity_g,
        quantity_base=item.quantity_base or item.quantity_g,
        unit=item.unit or "g",
        location=item.location or "pantry",
        price_per_100g=item.price_per_100g,
        updated_at=item.updated_at,
    )


def _to_out_shared(item: SharedInventoryItem, user_id: int) -> InventoryItemOut:
    return InventoryItemOut(
        id=item.id,
        user_id=user_id,  # caller's user_id for compatibility
        product_id=item.product_id,
        product_name=item.product.name,
        product_brand=item.product.brand,
        calories_per_100g=item.product.calories_per_100g,
        quantity_g=item.quantity_g,
        quantity_base=item.quantity_base or item.quantity_g,
        unit=item.unit or "g",
        location=item.location or "pantry",
        price_per_100g=item.price_per_100g,
        updated_at=item.updated_at,
    )


def _log_change(
    db: Session,
    user_id: int,
    item_id: int | None,
    product_id: int | None,
    quantity_change: float,
    unit: str,
    quantity_base_change: float,
    log_type: str,
    price_per_unit: float | None = None,
    notes: str | None = None,
) -> None:
    """Create an inventory log entry (does NOT commit)."""
    db.add(
        InventoryLog(
            user_id=user_id,
            item_id=item_id,
            product_id=product_id,
            quantity_change=quantity_change,
            unit=unit,
            quantity_base_change=quantity_base_change,
            log_type=log_type,
            price_per_unit=price_per_unit,
            notes=notes,
        )
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[InventoryItemOut])
def list_inventory(
    location: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[InventoryItemOut]:
    friendship = _get_active_shared_friendship(db, user.id)

    if friendship:
        q = select(SharedInventoryItem).where(SharedInventoryItem.friendship_id == friendship.id)
        if location:
            q = q.where(SharedInventoryItem.location == location)
        items = list(db.scalars(q))
        items.sort(key=lambda i: i.product.name.lower())
        return [_to_out_shared(i, user.id) for i in items]

    q = select(InventoryItem).where(InventoryItem.user_id == user.id)
    if location:
        q = q.where(InventoryItem.location == location)
    items = list(db.scalars(q))
    items.sort(key=lambda i: i.product.name.lower())
    return [_to_out_personal(i) for i in items]


@router.post("", response_model=InventoryItemOut, status_code=status.HTTP_201_CREATED)
def upsert_inventory(
    payload: InventoryItemIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InventoryItemOut:
    """Add or update item. Uses shared table if shared_inventory is active.

    The `quantity_base` is added to the existing stock (in the item's unit).
    The canonical `quantity_g` is also updated using the unit conversion factor.
    A log entry of type `purchase` is recorded.
    """
    friendship = _get_active_shared_friendship(db, user.id)

    # Compute grams equivalent for the incoming quantity
    delta_g = to_grams(db, payload.quantity_base, payload.unit, payload.product_id)

    if friendship:
        existing = db.scalar(
            select(SharedInventoryItem).where(
                SharedInventoryItem.friendship_id == friendship.id,
                SharedInventoryItem.product_id == payload.product_id,
            )
        )
        if existing:
            # Increment quantity in the existing unit if it matches, else just add grams
            if existing.unit == payload.unit:
                existing.quantity_base += payload.quantity_base
            else:
                # different unit: convert existing to grams first, then track grams only
                existing.quantity_base = (existing.quantity_g + delta_g)
                existing.unit = "g"
            existing.quantity_g += delta_g
            existing.location = payload.location
            if payload.price_per_100g is not None:
                existing.price_per_100g = payload.price_per_100g
            existing.updated_at = datetime.now(timezone.utc)
            _log_change(
                db,
                user_id=user.id,
                item_id=None,  # shared_inventory_items ≠ inventory_items FK
                product_id=existing.product_id,
                quantity_change=payload.quantity_base,
                unit=payload.unit,
                quantity_base_change=delta_g,
                log_type="purchase",
                price_per_unit=payload.price_per_100g,
            )
            db.commit()
            db.refresh(existing)
            return _to_out_shared(existing, user.id)

        item = SharedInventoryItem(
            friendship_id=friendship.id,
            product_id=payload.product_id,
            quantity_g=delta_g,
            quantity_base=payload.quantity_base,
            unit=payload.unit,
            location=payload.location,
            price_per_100g=payload.price_per_100g,
            added_by_user_id=user.id,
        )
        db.add(item)
        db.flush()  # get item.id
        _log_change(
            db,
            user_id=user.id,
            item_id=None,  # shared_inventory_items ≠ inventory_items FK
            product_id=item.product_id,
            quantity_change=payload.quantity_base,
            unit=payload.unit,
            quantity_base_change=delta_g,
            log_type="purchase",
            price_per_unit=payload.price_per_100g,
        )
        db.commit()
        db.refresh(item)
        return _to_out_shared(item, user.id)

    # Personal inventory
    existing = db.scalar(
        select(InventoryItem).where(
            InventoryItem.user_id == user.id,
            InventoryItem.product_id == payload.product_id,
        )
    )
    if existing:
        if existing.unit == payload.unit:
            existing.quantity_base += payload.quantity_base
        else:
            existing.quantity_base = (existing.quantity_g + delta_g)
            existing.unit = "g"
        existing.quantity_g += delta_g
        existing.location = payload.location
        if payload.price_per_100g is not None:
            existing.price_per_100g = payload.price_per_100g
        existing.updated_at = datetime.now(timezone.utc)
        _log_change(
            db,
            user_id=user.id,
            item_id=existing.id,
            product_id=existing.product_id,
            quantity_change=payload.quantity_base,
            unit=payload.unit,
            quantity_base_change=delta_g,
            log_type="purchase",
            price_per_unit=payload.price_per_100g,
        )
        db.commit()
        db.refresh(existing)
        return _to_out_personal(existing)

    item = InventoryItem(
        user_id=user.id,
        product_id=payload.product_id,
        quantity_g=delta_g,
        quantity_base=payload.quantity_base,
        unit=payload.unit,
        location=payload.location,
        price_per_100g=payload.price_per_100g,
    )
    db.add(item)
    db.flush()
    _log_change(
        db,
        user_id=user.id,
        item_id=item.id,
        product_id=item.product_id,
        quantity_change=payload.quantity_base,
        unit=payload.unit,
        quantity_base_change=delta_g,
        log_type="purchase",
        price_per_unit=payload.price_per_100g,
    )
    db.commit()
    db.refresh(item)
    return _to_out_personal(item)


@router.patch("/{item_id}", response_model=InventoryItemOut)
def update_inventory_item(
    item_id: int,
    payload: InventoryItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InventoryItemOut:
    friendship = _get_active_shared_friendship(db, user.id)

    if friendship:
        item = db.scalar(
            select(SharedInventoryItem).where(
                SharedInventoryItem.id == item_id,
                SharedInventoryItem.friendship_id == friendship.id,
            )
        )
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
        _apply_update_shared(db, item, payload)
        db.commit()
        db.refresh(item)
        return _to_out_shared(item, user.id)

    item = db.get(InventoryItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    _apply_update_personal(db, item, payload)
    db.commit()
    db.refresh(item)
    return _to_out_personal(item)


def _apply_update_personal(db: Session, item: InventoryItem, payload: InventoryItemUpdate) -> None:
    if payload.unit is not None:
        item.unit = payload.unit
    if payload.quantity_base is not None:
        item.quantity_base = payload.quantity_base
        # Recompute canonical grams
        item.quantity_g = to_grams(db, payload.quantity_base, item.unit, item.product_id)
    if payload.location is not None:
        item.location = payload.location
    if payload.price_per_100g is not None:
        item.price_per_100g = payload.price_per_100g
    item.updated_at = datetime.now(timezone.utc)


def _apply_update_shared(
    db: Session, item: SharedInventoryItem, payload: InventoryItemUpdate
) -> None:
    if payload.unit is not None:
        item.unit = payload.unit
    if payload.quantity_base is not None:
        item.quantity_base = payload.quantity_base
        item.quantity_g = to_grams(db, payload.quantity_base, item.unit, item.product_id)
    if payload.location is not None:
        item.location = payload.location
    if payload.price_per_100g is not None:
        item.price_per_100g = payload.price_per_100g
    item.updated_at = datetime.now(timezone.utc)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    friendship = _get_active_shared_friendship(db, user.id)

    if friendship:
        item = db.scalar(
            select(SharedInventoryItem).where(
                SharedInventoryItem.id == item_id,
                SharedInventoryItem.friendship_id == friendship.id,
            )
        )
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
        db.delete(item)
        db.commit()
        return

    item = db.get(InventoryItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    db.delete(item)
    db.commit()


# ── Consume / Adjust ──────────────────────────────────────────────────────────

@router.post("/{item_id}/consume", response_model=InventoryItemOut)
def consume_inventory_item(
    item_id: int,
    payload: InventoryConsumeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InventoryItemOut:
    """Subtract a quantity from stock. Creates a 'consume' log entry."""
    friendship = _get_active_shared_friendship(db, user.id)

    consume_g = to_grams(db, payload.quantity, payload.unit)
    consume_in_unit = payload.quantity

    if friendship:
        item = db.scalar(
            select(SharedInventoryItem).where(
                SharedInventoryItem.id == item_id,
                SharedInventoryItem.friendship_id == friendship.id,
            )
        )
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
        # Convert consume_in_unit to the item's unit if needed
        if item.unit != payload.unit:
            # Use grams as bridge: in item's unit = consume_g / factor(item.unit→g)
            item_factor = get_conversion_factor(db, item.unit, "g", item.product_id)
            consume_in_item_unit = consume_g / item_factor if item_factor else consume_g
        else:
            consume_in_item_unit = consume_in_unit

        item.quantity_g = max(0.0, item.quantity_g - consume_g)
        item.quantity_base = max(0.0, item.quantity_base - consume_in_item_unit)
        item.updated_at = datetime.now(timezone.utc)
        _log_change(
            db,
            user_id=user.id,
            item_id=None,  # shared_inventory_items ≠ inventory_items FK
            product_id=item.product_id,
            quantity_change=-payload.quantity,
            unit=payload.unit,
            quantity_base_change=-consume_g,
            log_type="consume",
            price_per_unit=item.price_per_100g,
            notes=payload.notes,
        )
        db.commit()
        db.refresh(item)
        return _to_out_shared(item, user.id)

    item = db.get(InventoryItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")

    if item.unit != payload.unit:
        item_factor = get_conversion_factor(db, item.unit, "g", item.product_id)
        consume_in_item_unit = consume_g / item_factor if item_factor else consume_g
    else:
        consume_in_item_unit = consume_in_unit

    item.quantity_g = max(0.0, item.quantity_g - consume_g)
    item.quantity_base = max(0.0, item.quantity_base - consume_in_item_unit)
    item.updated_at = datetime.now(timezone.utc)
    _log_change(
        db,
        user_id=user.id,
        item_id=item.id,
        product_id=item.product_id,
        quantity_change=-payload.quantity,
        unit=payload.unit,
        quantity_base_change=-consume_g,
        log_type="consume",
        price_per_unit=item.price_per_100g,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(item)
    return _to_out_personal(item)


@router.post("/{item_id}/adjust", response_model=InventoryItemOut)
def adjust_inventory_item(
    item_id: int,
    payload: InventoryAdjustIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InventoryItemOut:
    """Set absolute quantity (used for stock-count corrections). Logs the delta."""
    friendship = _get_active_shared_friendship(db, user.id)

    new_g = to_grams(db, payload.new_quantity, payload.unit)

    if friendship:
        item = db.scalar(
            select(SharedInventoryItem).where(
                SharedInventoryItem.id == item_id,
                SharedInventoryItem.friendship_id == friendship.id,
            )
        )
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")

        delta_g = new_g - item.quantity_g
        item.quantity_g = new_g
        item.quantity_base = payload.new_quantity
        item.unit = payload.unit
        item.updated_at = datetime.now(timezone.utc)
        _log_change(
            db,
            user_id=user.id,
            item_id=None,  # shared_inventory_items ≠ inventory_items FK
            product_id=item.product_id,
            quantity_change=payload.new_quantity,
            unit=payload.unit,
            quantity_base_change=delta_g,
            log_type="adjust",
            notes=payload.reason,
        )
        db.commit()
        db.refresh(item)
        return _to_out_shared(item, user.id)

    item = db.get(InventoryItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")

    delta_g = new_g - item.quantity_g
    item.quantity_g = new_g
    item.quantity_base = payload.new_quantity
    item.unit = payload.unit
    item.updated_at = datetime.now(timezone.utc)
    _log_change(
        db,
        user_id=user.id,
        item_id=item.id,
        product_id=item.product_id,
        quantity_change=payload.new_quantity,
        unit=payload.unit,
        quantity_base_change=delta_g,
        log_type="adjust",
        notes=payload.reason,
    )
    db.commit()
    db.refresh(item)
    return _to_out_personal(item)


# ── Logs ──────────────────────────────────────────────────────────────────────

@router.get("/logs", response_model=list[InventoryLogOut])
def list_inventory_logs(
    item_id: int | None = Query(default=None),
    log_type: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[InventoryLogOut]:
    q = (
        select(InventoryLog)
        .where(InventoryLog.user_id == user.id)
        .order_by(InventoryLog.created_at.desc())
        .limit(limit)
    )
    if item_id is not None:
        q = q.where(InventoryLog.item_id == item_id)
    if log_type:
        q = q.where(InventoryLog.log_type == log_type)
    logs = list(db.scalars(q))
    return [
        InventoryLogOut(
            id=log.id,
            user_id=log.user_id,
            item_id=log.item_id,
            product_id=log.product_id,
            product_name=log.product.name if log.product else None,
            quantity_change=log.quantity_change,
            unit=log.unit,
            quantity_base_change=log.quantity_base_change,
            log_type=log.log_type,
            price_per_unit=log.price_per_unit,
            notes=log.notes,
            created_at=log.created_at,
        )
        for log in logs
    ]


# ── Cost summary ──────────────────────────────────────────────────────────────

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

    # Build price map from whichever inventory is active
    price_map: dict[int, float] = {}
    friendship = _get_active_shared_friendship(db, user.id)
    if friendship:
        for item in db.scalars(
            select(SharedInventoryItem).where(SharedInventoryItem.friendship_id == friendship.id)
        ):
            if item.price_per_100g is not None:
                price_map[item.product_id] = item.price_per_100g
    else:
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


# ── Unit conversions ──────────────────────────────────────────────────────────

@router.get("/conversions", response_model=list[UnitConversionOut])
def list_conversions(
    from_unit: str | None = Query(default=None),
    to_unit: str | None = Query(default=None),
    product_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[UnitConversionOut]:
    q = select(UnitConversion)
    if from_unit:
        q = q.where(UnitConversion.from_unit == from_unit)
    if to_unit:
        q = q.where(UnitConversion.to_unit == to_unit)
    if product_id is not None:
        q = q.where(
            or_(UnitConversion.product_id == product_id, UnitConversion.product_id.is_(None))
        )
    rows = list(db.scalars(q))
    return [
        UnitConversionOut(
            from_unit=r.from_unit,
            to_unit=r.to_unit,
            factor=r.factor,
            product_id=r.product_id,
        )
        for r in rows
    ]
