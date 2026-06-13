import csv
import io
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import DiaryEntry, Product, User, ExerciseSession
from app.models.cheat_day import CheatDayLog
from app.models.diary import MealType
from app.models.friendship import Friendship, FriendshipStatus
from app.schemas.diary import (
    MEAL_LABELS,
    MEAL_ORDER,
    DayTotals,
    DaySummary,
    DiaryEntryCreate,
    DiaryEntryOut,
    DiaryEntryUpdate,
    MealSection,
)
from app.schemas.misc import DiaryRecipeCreate
from app.services.streak_service import calculate_streak, milestone_hit
from app.services.notification_scheduler import send_milestone_push

router = APIRouter(prefix="/diary", tags=["diary"])


def _can_log_for_user(db: Session, actor_id: int, target_user_id: int) -> bool:
    if actor_id == target_user_id:
        return True

    # Case 1: actor is requester, target is receiver, receiver gave permission
    as_requester = db.scalar(
        select(Friendship.id)
        .where(
            Friendship.requester_id == actor_id,
            Friendship.receiver_id == target_user_id,
            Friendship.status == FriendshipStatus.accepted,
            Friendship.can_add_food.is_(True),
        )
        .limit(1)
    )
    if as_requester is not None:
        return True

    # Case 2: actor is receiver, target is requester, requester gave permission
    as_receiver = db.scalar(
        select(Friendship.id)
        .where(
            Friendship.requester_id == target_user_id,
            Friendship.receiver_id == actor_id,
            Friendship.status == FriendshipStatus.accepted,
            Friendship.can_add_food_requester.is_(True),
        )
        .limit(1)
    )
    return as_receiver is not None


def _build_entry(
    user_id: int, product: Product, grams: float, consumed_at: datetime, meal_type: MealType,
    recipe_id: int | None = None,
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
        recipe_id=recipe_id,
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

    # Modo "solo para la pareja": no se crea entrada para el usuario actual
    if payload.only_for_user_id and payload.only_for_user_id != user.id:
        other = db.get(User, payload.only_for_user_id)
        if not other:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Other user not found")
        if not _can_log_for_user(db, user.id, other.id):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "No tienes permiso para registrar comida en el diario de este usuario",
            )
        created = [_build_entry(other.id, product, payload.grams, payload.consumed_at, meal_type)]
    else:
        created = [_build_entry(user.id, product, payload.grams, payload.consumed_at, meal_type)]
        if payload.also_for_user_id and payload.also_for_user_id != user.id:
            other = db.get(User, payload.also_for_user_id)
            if not other:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Other user not found")
            if not _can_log_for_user(db, user.id, other.id):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "No tienes permiso para registrar comida en el diario de este usuario",
                )
            created.append(_build_entry(other.id, product, payload.grams, payload.consumed_at, meal_type))

    # Calculate streak BEFORE commit to detect milestone
    old_streak = calculate_streak(db, user.id)

    db.add_all(created)
    db.commit()
    for e in created:
        db.refresh(e)

    # Check for streak milestone and send push if hit
    new_streak = calculate_streak(db, user.id)
    hit = milestone_hit(old_streak, new_streak)
    if hit:
        try:
            send_milestone_push(db, user.id, hit)
        except Exception:
            pass  # non-critical

    return created


@router.post("/recipe", response_model=list[DiaryEntryOut], status_code=status.HTTP_201_CREATED)
def log_recipe(
    payload: DiaryRecipeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DiaryEntry]:
    """Log all ingredients of a recipe at once, tagging each entry with recipe_id."""
    from app.models import Recipe, RecipeIngredient  # noqa: F401 (avoid circular at module level)
    from sqlalchemy.orm import selectinload

    recipe = db.scalar(
        select(Recipe)
        .options(selectinload(Recipe.ingredients))
        .where(Recipe.id == payload.recipe_id)
    )
    if not recipe:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    if recipe.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your recipe")

    meal_type = MealType(payload.meal_type)
    user_ids = [user.id]

    if payload.also_for_user_id and payload.also_for_user_id != user.id:
        other = db.get(User, payload.also_for_user_id)
        if not other:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Other user not found")
        if not _can_log_for_user(db, user.id, other.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para registrar en el diario de este usuario")
        user_ids.append(other.id)

    entries: list[DiaryEntry] = []
    for uid in user_ids:
        for ing in recipe.ingredients:
            product = db.get(Product, ing.product_id)
            if not product:
                continue
            entries.append(_build_entry(
                uid, product, ing.grams, payload.consumed_at, meal_type,
                recipe_id=recipe.id,
            ))

    db.add_all(entries)
    db.commit()
    for e in entries:
        db.refresh(e)
    return entries


@router.get("/day", response_model=DaySummary)
def day_summary(
    day: date = Query(default_factory=lambda: datetime.now(timezone.utc).date()),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DaySummary:
    # Free users can only see the last 7 days
    if not user.is_premium_or_trial:
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=6)
        if day < cutoff:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="premium_required",
            )
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

    # Consultar sesión de ejercicio del día
    exercise_session = db.scalar(
        select(ExerciseSession).where(
            ExerciseSession.user_id == user.id,
            ExerciseSession.session_date == day,
        )
    )
    calories_burned = exercise_session.total_calories if exercise_session else 0.0

    return DaySummary(
        date=day.isoformat(),
        totals=totals,
        meals=meals,
        entries=entry_outs,
        calories_burned=calories_burned,
        net_calories=totals.calories - calories_burned,
        has_exercise=exercise_session is not None,
    )


@router.get("/days", response_model=list[DaySummary])
def days_range(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DaySummary]:
    """Batch summary for a date range — replaces N individual /diary/day calls."""
    if not user.is_premium_or_trial:
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=6)
        if date_from < cutoff:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="premium_required",
            )

    start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)

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

    exercise_sessions = list(
        db.scalars(
            select(ExerciseSession).where(
                ExerciseSession.user_id == user.id,
                ExerciseSession.session_date >= date_from,
                ExerciseSession.session_date <= date_to,
            )
        )
    )
    exercise_by_date = {s.session_date: s for s in exercise_sessions}

    entries_by_date: dict[date, list[DiaryEntry]] = {}
    for entry in entries:
        day = entry.consumed_at.date()
        entries_by_date.setdefault(day, []).append(entry)

    all_days = sorted(set(entries_by_date.keys()) | set(exercise_by_date.keys()))
    summaries = []
    for day in all_days:
        day_entries = entries_by_date.get(day, [])
        totals = DayTotals(
            calories=sum(e.calories for e in day_entries),
            protein=sum(e.protein for e in day_entries),
            carbs=sum(e.carbs for e in day_entries),
            fat=sum(e.fat for e in day_entries),
        )
        entry_outs = [DiaryEntryOut.model_validate(e) for e in day_entries]
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
        exercise_session = exercise_by_date.get(day)
        calories_burned = exercise_session.total_calories if exercise_session else 0.0
        summaries.append(DaySummary(
            date=day.isoformat(),
            totals=totals,
            meals=meals,
            entries=entry_outs,
            calories_burned=calories_burned,
            net_calories=totals.calories - calories_burned,
            has_exercise=exercise_session is not None,
        ))

    return summaries


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
        product = e.product
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


@router.get("/streak")
def get_streak(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Streak + active days for the last 30 days — both values the profile needs in one call."""
    from sqlalchemy import func, cast, Date as SADate

    since = date.today() - timedelta(days=29)
    active_days = db.scalar(
        select(func.count(func.distinct(cast(DiaryEntry.consumed_at, SADate)))).where(
            DiaryEntry.user_id == user.id,
            cast(DiaryEntry.consumed_at, SADate) >= since,
        )
    ) or 0
    return {"streak": calculate_streak(db, user.id), "active_days": active_days}


@router.post("/copy-from-yesterday", status_code=status.HTTP_201_CREATED)
def copy_from_yesterday(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Copy all diary entries from yesterday into today, preserving meal types."""
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    y_start = datetime.combine(yesterday, time.min, tzinfo=timezone.utc)
    y_end = datetime.combine(yesterday, time.max, tzinfo=timezone.utc)
    yesterday_entries = list(db.scalars(
        select(DiaryEntry).where(
            DiaryEntry.user_id == user.id,
            DiaryEntry.consumed_at >= y_start,
            DiaryEntry.consumed_at <= y_end,
        )
    ))

    if not yesterday_entries:
        return {"copied": 0}

    now = datetime.now(timezone.utc)
    new_entries = [
        DiaryEntry(
            user_id=e.user_id,
            product_id=e.product_id,
            grams=e.grams,
            calories=e.calories,
            protein=e.protein,
            carbs=e.carbs,
            fat=e.fat,
            meal_type=e.meal_type,
            consumed_at=now,
        )
        for e in yesterday_entries
    ]
    db.add_all(new_entries)
    db.commit()
    return {"copied": len(new_entries)}


@router.patch("/{entry_id}", response_model=DiaryEntryOut)
def update_entry(
    entry_id: int,
    payload: DiaryEntryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DiaryEntry:
    entry = db.get(DiaryEntry, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entry not found")
    product = db.get(Product, entry.product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    factor = payload.grams / 100.0
    entry.grams = payload.grams
    entry.calories = product.calories_per_100g * factor
    entry.protein = product.protein_per_100g * factor
    entry.carbs = product.carbs_per_100g * factor
    entry.fat = product.fat_per_100g * factor
    if payload.meal_type is not None:
        entry.meal_type = MealType(payload.meal_type)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    also_for_user_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    entry = db.get(DiaryEntry, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entry not found")

    if also_for_user_id and also_for_user_id != user.id:
        if not _can_log_for_user(db, user.id, also_for_user_id):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "No tienes permiso para eliminar entradas de este usuario",
            )
        # Find the partner's entry with same product logged on same day
        entry_date = entry.consumed_at.date()
        p_start = datetime.combine(entry_date, time.min, tzinfo=timezone.utc)
        p_end = datetime.combine(entry_date, time.max, tzinfo=timezone.utc)
        partner_entry = db.scalar(
            select(DiaryEntry)
            .where(
                DiaryEntry.user_id == also_for_user_id,
                DiaryEntry.product_id == entry.product_id,
                DiaryEntry.consumed_at >= p_start,
                DiaryEntry.consumed_at <= p_end,
            )
            .limit(1)
        )
        if partner_entry:
            db.delete(partner_entry)

    db.delete(entry)
    db.commit()


@router.delete("/meal/{meal_type}", status_code=status.HTTP_204_NO_CONTENT)
def clear_meal(
    meal_type: str,
    day: date = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete all diary entries for a given meal_type on a given day."""
    try:
        mt = MealType(meal_type)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Meal type inválido")

    day_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    day_end   = datetime.combine(day, time.max, tzinfo=timezone.utc)

    entries = db.scalars(
        select(DiaryEntry).where(
            DiaryEntry.user_id == user.id,
            DiaryEntry.meal_type == mt,
            DiaryEntry.consumed_at >= day_start,
            DiaryEntry.consumed_at <= day_end,
        )
    ).all()

    for e in entries:
        db.delete(e)
    db.commit()
