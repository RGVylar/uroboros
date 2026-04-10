import csv
import io
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import DiaryEntry, Product, User
from app.models.diary import MealType
from app.schemas.diary import (
    MEAL_LABELS,
    MEAL_ORDER,
    DayTotals,
    DaySummary,
    DiaryEntryCreate,
    DiaryEntryOut,
    MealSection,
)

router = APIRouter(prefix="/diary", tags=["diary"])


def _build_entry(
    user_id: int, product: Product, grams: float, consumed_at: datetime, meal_type: MealType
) -> DiaryEntry:
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
        meal_type=meal_type,
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

    meal_type = MealType(payload.meal_type)
    created = [_build_entry(user.id, product, payload.grams, payload.consumed_at, meal_type)]

    if payload.also_for_user_id and payload.also_for_user_id != user.id:
        other = db.get(User, payload.also_for_user_id)
        if not other:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Other user not found")
        created.append(_build_entry(other.id, product, payload.grams, payload.consumed_at, meal_type))

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

    # Group by meal type in order
    entry_outs = [DiaryEntryOut.model_validate(e) for e in entries]
    meals = []
    for mt in MEAL_ORDER:
        meal_entries = [e for e in entry_outs if e.meal_type == mt]
        if meal_entries:
            meals.append(MealSection(
                meal_type=mt,
                label=MEAL_LABELS[mt],
                totals=DayTotals(
                    calories=sum(e.calories for e in meal_entries),
                    protein=sum(e.protein for e in meal_entries),
                    carbs=sum(e.carbs for e in meal_entries),
                    fat=sum(e.fat for e in meal_entries),
                ),
                entries=meal_entries,
            ))

    return DaySummary(
        date=day.isoformat(),
        totals=totals,
        meals=meals,
        entries=entry_outs,
    )


@router.get("/export.csv")
def export_csv(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export diary entries as CSV. Defaults to all history."""
    stmt = select(DiaryEntry).where(DiaryEntry.user_id == user.id)
    if date_from:
        stmt = stmt.where(DiaryEntry.consumed_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        stmt = stmt.where(DiaryEntry.consumed_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    stmt = stmt.order_by(DiaryEntry.consumed_at)
    entries = list(db.scalars(stmt))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "time", "meal_type", "product", "grams", "calories", "protein_g", "carbs_g", "fat_g"])

    for e in entries:
        product = db.get(Product, e.product_id)
        dt = e.consumed_at
        writer.writerow([
            dt.strftime("%Y-%m-%d"),
            dt.strftime("%H:%M"),
            e.meal_type.value if e.meal_type else "",
            product.name if product else f"#{e.product_id}",
            round(e.grams, 1),
            round(e.calories, 1),
            round(e.protein, 1),
            round(e.carbs, 1),
            round(e.fat, 1),
        ])

    output.seek(0)
    filename = f"uroboros_{user.id}"
    if date_from:
        filename += f"_{date_from}"
    if date_to:
        filename += f"_{date_to}"
    filename += ".csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
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
