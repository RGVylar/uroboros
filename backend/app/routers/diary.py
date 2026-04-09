from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import DiaryEntry, Product, User
from app.schemas.diary import DayTotals, DaySummary, DiaryEntryCreate, DiaryEntryOut

router = APIRouter(prefix="/diary", tags=["diary"])


def _build_entry(user_id: int, product: Product, grams: float, consumed_at: datetime) -> DiaryEntry:
    factor = grams / 100.0
    return DiaryEntry(
        user_id=user_id,
        product_id=product.id,
        grams=grams,
        calories=product.calories_per_100g * factor,
        protein=product.protein_per_100g * factor,
        carbs=product.carbs_per_100g * factor,
        fat=product.fat_per_100g * factor,
        consumed_at=consumed_at,
    )


@router.post("", response_model=list[DiaryEntryOut], status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: DiaryEntryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DiaryEntry]:
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    created = [_build_entry(user.id, product, payload.grams, payload.consumed_at)]

    if payload.also_for_user_id and payload.also_for_user_id != user.id:
        other = db.get(User, payload.also_for_user_id)
        if not other:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Other user not found")
        created.append(_build_entry(other.id, product, payload.grams, payload.consumed_at))

    db.add_all(created)
    db.commit()
    for e in created:
        db.refresh(e)
    return created


@router.get("/day", response_model=DaySummary)
def day_summary(
    day: date = Query(default_factory=lambda: datetime.now(timezone.utc).date()),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DaySummary:
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = datetime.combine(day, time.max, tzinfo=timezone.utc)
    entries = list(
        db.scalars(
            select(DiaryEntry)
            .where(
                DiaryEntry.user_id == user.id,
                DiaryEntry.consumed_at >= start,
                DiaryEntry.consumed_at <= end,
            )
            .order_by(DiaryEntry.consumed_at)
        )
    )
    totals = DayTotals(
        calories=sum(e.calories for e in entries),
        protein=sum(e.protein for e in entries),
        carbs=sum(e.carbs for e in entries),
        fat=sum(e.fat for e in entries),
    )
    return DaySummary(
        date=day.isoformat(),
        totals=totals,
        entries=[DiaryEntryOut.model_validate(e) for e in entries],
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    entry = db.get(DiaryEntry, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entry not found")
    db.delete(entry)
    db.commit()
