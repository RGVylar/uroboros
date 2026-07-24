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
from app.models.friendship import Friendship, FriendshipKind, FriendshipStatus
from app.models.supplement import SupplementLog, UserSupplement
from app.schemas.diary import (
    MEAL_LABELS,
    MEAL_ORDER,
    DayTotals,
    DaySummary,
    DiaryEntryCreate,
    DiaryEntryOut,
    DiaryEntryUpdate,
    MealConflictCheck,
    MealSection,
    MealTypeLiteral,
    PartnerEntryStatus,
)
from app.schemas.misc import DiaryRecipeCreate
from app.services.streak_service import calculate_streak, milestone_hit
from app.services.notification_scheduler import send_milestone_push

router = APIRouter(prefix="/diary", tags=["diary"])


def _restore_inventory_for_entry(db: Session, entry: DiaryEntry) -> None:
    """Devuelve al stock lo consumido por los logs de inventario ligados a `entry`.

    Se llama ANTES de borrar la entrada. No hace commit.
    """
    from datetime import timezone as _tz

    from app.models import InventoryItem, InventoryLog, SharedInventoryItem
    from app.routers.inventory import _get_active_shared_friendship, _log_change
    from app.services.unit_conversions import get_conversion_factor

    logs = db.scalars(
        select(InventoryLog).where(
            InventoryLog.diary_entry_id == entry.id,
            InventoryLog.log_type == "consume",
        )
    ).all()

    for log in logs:
        restore_qty = -log.quantity_change  # consume logs store negative amounts
        restore_g = -log.quantity_base_change
        if restore_qty <= 0 or restore_g <= 0:
            continue

        item: InventoryItem | SharedInventoryItem | None = None
        if log.item_id is not None:
            item = db.get(InventoryItem, log.item_id)
        elif log.product_id is not None:
            friendship = _get_active_shared_friendship(db, log.user_id)
            if friendship:
                item = db.scalar(
                    select(SharedInventoryItem).where(
                        SharedInventoryItem.friendship_id == friendship.id,
                        SharedInventoryItem.product_id == log.product_id,
                    )
                )
        # Evitar restauraciones dobles aunque el item ya no exista
        log.diary_entry_id = None
        if not item:
            continue

        if item.unit == log.unit:
            restore_in_item_unit = restore_qty
        else:
            factor = get_conversion_factor(db, item.unit, "g", item.product_id)
            restore_in_item_unit = restore_g / factor if factor else restore_g

        item.quantity_g += restore_g
        item.quantity_base += restore_in_item_unit
        item.updated_at = datetime.now(_tz.utc)
        _log_change(
            db,
            user_id=log.user_id,
            item_id=log.item_id,
            product_id=log.product_id,
            quantity_change=restore_qty,
            unit=log.unit,
            quantity_base_change=restore_g,
            log_type="adjust",
            notes="Reposición: entrada del diario eliminada",
        )

# Free tier can browse the last N days of history; older days are premium.
FREE_HISTORY_DAYS = 90


def _can_log_for_user(db: Session, actor_id: int, target_user_id: int) -> bool:
    """Whether `actor` may write in `target`'s diary.

    Partners only. Logging each other's meals is an intimate, household-level
    thing, so it needs both a partnership and the target's opt-in flag — not just
    the flag. The flag alone used to be enough, and it defaulted to true on every
    request ever sent, so any friend could write. kind == partner closes that.
    """
    if actor_id == target_user_id:
        return True

    # Case 1: actor is requester, target is receiver, receiver gave permission
    as_requester = db.scalar(
        select(Friendship.id)
        .where(
            Friendship.requester_id == actor_id,
            Friendship.receiver_id == target_user_id,
            Friendship.status == FriendshipStatus.accepted,
            Friendship.kind == FriendshipKind.partner,
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
            Friendship.kind == FriendshipKind.partner,
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

    # Calculate streak BEFORE commit to detect milestone. Still two calls (not
    # collapsed into old_streak + 1) because consumed_at is client-supplied and
    # entries can be backdated to fill a past gap, which can jump the streak by
    # more than one day — calculate_streak is now 2 fixed queries instead of
    # O(days), so the second call is cheap rather than something to eliminate.
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


@router.get("/meal-check", response_model=MealConflictCheck)
def meal_conflict_check(
    user_id: int,
    day: date,
    meal_type: MealTypeLiteral,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MealConflictCheck:
    """
    Avisa si `user_id` ya tiene entradas en `meal_type` ese día — para que quien
    registra comida para su pareja (also_for_user_id / only_for_user_id) sepa
    que ya hay algo ahí antes de añadir más, sin ver el resto de su diario.
    """
    if user_id != user.id and not _can_log_for_user(db, user.id, user_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No tienes permiso para consultar el diario de este usuario",
        )

    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = datetime.combine(day, time.max, tzinfo=timezone.utc)
    entries = list(
        db.scalars(
            select(DiaryEntry)
            .where(
                DiaryEntry.user_id == user_id,
                DiaryEntry.meal_type == MealType(meal_type),
                DiaryEntry.consumed_at >= start,
                DiaryEntry.consumed_at <= end,
            )
            .order_by(DiaryEntry.consumed_at)
        )
    )
    return MealConflictCheck(
        has_entries=len(entries) > 0,
        count=len(entries),
        calories=sum(e.calories for e in entries),
        product_names=[e.product.name for e in entries if e.product],
    )


@router.get("/partner-entry", response_model=PartnerEntryStatus)
def partner_entry_status(
    user_id: int,
    product_id: int,
    day: date,
    meal_type: MealTypeLiteral,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PartnerEntryStatus:
    """
    ¿`user_id` (la pareja) ya tiene ESTE producto en ESTA comida ese día?
    Para el modal de editar: decidir si mostrar "ya lo tiene (Xg)" o "añadírselo".
    Empareja por producto + comida + día (no solo por día), así distingue el mismo
    alimento en desayuno vs cena.
    """
    if user_id != user.id and not _can_log_for_user(db, user.id, user_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No tienes permiso para consultar el diario de este usuario",
        )

    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = datetime.combine(day, time.max, tzinfo=timezone.utc)
    entries = list(
        db.scalars(
            select(DiaryEntry)
            .where(
                DiaryEntry.user_id == user_id,
                DiaryEntry.product_id == product_id,
                DiaryEntry.meal_type == MealType(meal_type),
                DiaryEntry.consumed_at >= start,
                DiaryEntry.consumed_at <= end,
            )
            .order_by(DiaryEntry.consumed_at)
        )
    )
    if not entries:
        return PartnerEntryStatus(count=0)
    first = entries[0]
    return PartnerEntryStatus(entry_id=first.id, grams=first.grams, count=len(entries))


@router.get("/day", response_model=DaySummary)
def day_summary(
    day: date = Query(default_factory=lambda: datetime.now(timezone.utc).date()),
    user_id: int | None = Query(None),  # read a partner's day (household permission)
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DaySummary:
    # Which diary are we reading — your own, or your partner's?
    target_id = user_id if user_id is not None else user.id
    if target_id != user.id and not _can_log_for_user(db, user.id, target_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    # Free users can only browse recent history (gate applies to the actor)
    if not user.is_premium_or_trial:
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=FREE_HISTORY_DAYS - 1)
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
                DiaryEntry.user_id == target_id,
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
            ExerciseSession.user_id == target_id,
            ExerciseSession.session_date == day,
        )
    )
    calories_burned = exercise_session.total_calories if exercise_session else 0.0

    # Estado de suplementos: solo tiene sentido para "hoy" (los logs son diarios).
    supplements_done: bool | None = None
    if day == datetime.now(timezone.utc).date():
        weekday = day.weekday()
        all_supps = list(db.scalars(
            select(UserSupplement)
            .where(UserSupplement.user_id == target_id)
            .order_by(UserSupplement.position, UserSupplement.id)
        ))
        scheduled = [s for s in all_supps if s.active_today(weekday)]
        if scheduled:
            taken_ids = set(db.scalars(
                select(SupplementLog.supplement_id).where(
                    SupplementLog.user_id == target_id,
                    SupplementLog.logged_date == day,
                )
            ))
            supplements_done = all(s.id in taken_ids for s in scheduled)

    return DaySummary(
        date=day.isoformat(),
        totals=totals,
        meals=meals,
        entries=entry_outs,
        calories_burned=calories_burned,
        net_calories=totals.calories - calories_burned,
        has_exercise=exercise_session is not None,
        supplements_done=supplements_done,
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
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=FREE_HISTORY_DAYS - 1)
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
    # Permite editar tu entrada o la de tu pareja (misma capacidad household que añadir).
    if not entry or (entry.user_id != user.id and not _can_log_for_user(db, user.id, entry.user_id)):
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
    also_for_user_id: int | None = Query(None),  # borrar la mía + la copia de la pareja
    only_for_user_id: int | None = Query(None),  # borrar SOLO la copia de la pareja, conservar la mía
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    entry = db.get(DiaryEntry, entry_id)
    # Permite borrar tu entrada o la de tu pareja (misma capacidad household que añadir).
    if not entry or (entry.user_id != user.id and not _can_log_for_user(db, user.id, entry.user_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entry not found")

    # ¿Hay que tocar la copia de la pareja? Se empareja por producto + comida + día
    # a partir de ESTA entrada (also_for = además de la mía; only_for = solo la suya).
    partner_target = also_for_user_id or only_for_user_id
    if partner_target and partner_target != user.id:
        if not _can_log_for_user(db, user.id, partner_target):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "No tienes permiso para eliminar entradas de este usuario",
            )
        entry_date = entry.consumed_at.date()
        p_start = datetime.combine(entry_date, time.min, tzinfo=timezone.utc)
        p_end = datetime.combine(entry_date, time.max, tzinfo=timezone.utc)
        partner_entry = db.scalar(
            select(DiaryEntry)
            .where(
                DiaryEntry.user_id == partner_target,
                DiaryEntry.product_id == entry.product_id,
                DiaryEntry.meal_type == entry.meal_type,
                DiaryEntry.consumed_at >= p_start,
                DiaryEntry.consumed_at <= p_end,
            )
            .limit(1)
        )
        if partner_entry:
            _restore_inventory_for_entry(db, partner_entry)
            db.delete(partner_entry)

    # Mi entrada se borra salvo que sea "solo para la pareja".
    if not only_for_user_id:
        _restore_inventory_for_entry(db, entry)
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
        _restore_inventory_for_entry(db, e)
        db.delete(e)
    db.commit()
