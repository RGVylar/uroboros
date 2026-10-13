from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models import DiaryEntry, Pot, PotIngredient, Product, Recipe, User
from app.models.diary import MealType
from app.routers.diary import _build_entry, _can_log_for_user
from app.routers.recipes import _can_see, _circles
from app.schemas.pot import PotCreate, PotLogIn, PotOut, PotUpdate
from app.services.pots import EMPTY_EPS, eaten_fractions, pot_out, remaining_fraction

router = APIRouter(prefix="/pots", tags=["pots"])

# Una olla olvidada (nadie la terminó) deja de salir pasado este tiempo.
ACTIVE_DAYS = 30


def _load(db: Session, pot_id: int, user: User) -> Pot:
    pot = db.scalar(
        select(Pot).options(selectinload(Pot.ingredients)).where(Pot.id == pot_id)
    )
    if not pot or user.id not in (pot.owner_id, pot.partner_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pot not found")
    return pot


@router.get("", response_model=list[PotOut])
def list_pots(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    """Las ollas en marcha: mías o de mi pareja, sin terminar y con algo dentro.
    Una olla vacía no se borra: si alguien borra una entrada, vuelve a salir."""
    since = datetime.now(timezone.utc) - timedelta(days=ACTIVE_DAYS)
    pots = db.scalars(
        select(Pot)
        .options(selectinload(Pot.ingredients))
        .where(
            or_(Pot.owner_id == user.id, Pot.partner_id == user.id),
            Pot.finished_at.is_(None),
            Pot.created_at >= since,
        )
        .order_by(Pot.created_at.desc())
    ).all()
    out = [pot_out(db, p) for p in pots]
    return [o for o in out if o["remaining"] > EMPTY_EPS]


@router.post("", response_model=PotOut, status_code=status.HTTP_201_CREATED)
def create_pot(payload: PotCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    if payload.recipe_id is not None:
        recipe = db.scalar(
            select(Recipe).options(selectinload(Recipe.ingredients)).where(Recipe.id == payload.recipe_id)
        )
        if not recipe or (recipe.owner_id != user.id and not _can_see(db, user.id, recipe)):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
        items = [(i.product_id, i.grams) for i in recipe.ingredients]
    else:
        items = [(i.product_id, i.grams) for i in payload.ingredients or []]
    if not items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pot has no ingredients")
    known = set(db.scalars(select(Product.id).where(Product.id.in_([pid for pid, _ in items]))))
    if any(pid not in known for pid, _ in items):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown product")

    partner_id = _circles(db, user.id)[0] if payload.shared else None
    pot = Pot(
        owner_id=user.id,
        partner_id=partner_id,
        name=payload.name.strip(),
        servings=payload.servings,
        cooked_weight=payload.cooked_weight,
        ingredients=[PotIngredient(product_id=pid, grams=g) for pid, g in items],
    )
    db.add(pot)
    db.commit()
    return pot_out(db, _load(db, pot.id, user))


@router.get("/{pot_id}", response_model=PotOut)
def get_pot(pot_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return pot_out(db, _load(db, pot_id, user))


@router.patch("/{pot_id}", response_model=PotOut)
def update_pot(
    pot_id: int, payload: PotUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    pot = _load(db, pot_id, user)
    if payload.name is not None:
        pot.name = payload.name.strip()
    if payload.servings is not None:
        pot.servings = payload.servings
    if payload.clear_weight:
        pot.cooked_weight = None
    elif payload.weight_now is not None:
        # Pesada más tarde: lo que hay ahora es la parte que queda. El peso
        # total es ese peso escalado a la olla entera.
        left = remaining_fraction(eaten_fractions(db, pot)[0])
        if left <= EMPTY_EPS:
            raise HTTPException(status.HTTP_409_CONFLICT, "pot_empty")
        pot.cooked_weight = round(payload.weight_now / left, 1)
    db.commit()
    return pot_out(db, _load(db, pot_id, user))


@router.post("/{pot_id}/finish", response_model=PotOut)
def finish_pot(pot_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    """Se acabó o se tiró lo que sobraba. Lo apuntado no se toca."""
    pot = _load(db, pot_id, user)
    pot.finished_at = datetime.now(timezone.utc)
    db.commit()
    return pot_out(db, pot)


@router.post("/{pot_id}/log", response_model=PotOut, status_code=status.HTTP_201_CREATED)
def log_from_pot(
    pot_id: int, payload: PotLogIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    pot = _load(db, pot_id, user)
    if pot.finished_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "pot_finished")

    # Para quién: el mismo trío que el resto del diario.
    other_id = payload.only_for_user_id or payload.also_for_user_id
    if other_id and other_id != user.id:
        if other_id not in (pot.owner_id, pot.partner_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not shared with that user")
        if not _can_log_for_user(db, user.id, other_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para registrar en el diario de este usuario")
        user_ids = [other_id] if payload.only_for_user_id else [user.id, other_id]
    else:
        user_ids = [user.id]

    left = remaining_fraction(eaten_fractions(db, pot)[0])
    if left <= EMPTY_EPS:
        raise HTTPException(status.HTTP_409_CONFLICT, "pot_empty")

    # Parte de la olla para cada persona.
    if payload.rest:
        fraction = left / len(user_ids)
    elif payload.grams is not None:
        if not pot.cooked_weight:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "pot_not_weighed")
        fraction = payload.grams / pot.cooked_weight
    else:
        fraction = payload.servings / pot.servings
    # Nadie se lleva más de lo que queda: si se pasa, se reparte lo que hay.
    fraction = min(fraction, left / len(user_ids))

    meal_type = MealType(payload.meal_type)
    entries: list[DiaryEntry] = []
    for uid in user_ids:
        for ing in pot.ingredients:
            entry = _build_entry(uid, ing.product, ing.grams * fraction, payload.consumed_at, meal_type)
            entry.pot_id = pot.id
            entries.append(entry)
    db.add_all(entries)
    db.commit()
    return pot_out(db, pot)
