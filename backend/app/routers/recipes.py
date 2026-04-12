from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models import Friendship, FriendshipStatus, Recipe, RecipeIngredient, User
from app.schemas.misc import RecipeIn, RecipeOut, SharedRecipeOut

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _load_recipe(db: Session, recipe_id: int) -> Recipe:
    stmt = (
        select(Recipe)
        .options(selectinload(Recipe.ingredients).joinedload(RecipeIngredient.product))
        .where(Recipe.id == recipe_id)
    )
    return db.scalars(stmt).first()


def _friend_ids(db: Session, user_id: int) -> set[int]:
    stmt = select(Friendship).where(
        or_(Friendship.requester_id == user_id, Friendship.receiver_id == user_id),
        Friendship.status == FriendshipStatus.accepted,
    )
    ids: set[int] = set()
    for f in db.scalars(stmt):
        ids.add(f.receiver_id if f.requester_id == user_id else f.requester_id)
    return ids


# ── GET /recipes/shared  (must be before /{recipe_id}) ──────────────────────
@router.get("/shared", response_model=list[SharedRecipeOut])
def list_shared_recipes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    friend_ids = _friend_ids(db, user.id)
    if not friend_ids:
        return []

    stmt = (
        select(Recipe, User)
        .join(User, Recipe.owner_id == User.id)
        .options(selectinload(Recipe.ingredients).joinedload(RecipeIngredient.product))
        .where(Recipe.owner_id.in_(friend_ids), Recipe.is_shared == True)  # noqa: E712
        .order_by(Recipe.name)
    )
    results = []
    for recipe, owner in db.execute(stmt):
        results.append({
            "id": recipe.id,
            "name": recipe.name,
            "owner_id": recipe.owner_id,
            "is_shared": recipe.is_shared,
            "ingredients": recipe.ingredients,
            "owner_name": owner.name,
        })
    return results


# ── GET /recipes ─────────────────────────────────────────────────────────────
@router.get("", response_model=list[RecipeOut])
def list_recipes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Recipe]:
    stmt = (
        select(Recipe)
        .options(selectinload(Recipe.ingredients).joinedload(RecipeIngredient.product))
        .where(Recipe.owner_id == user.id)
        .order_by(Recipe.name)
    )
    return list(db.scalars(stmt))


# ── POST /recipes ─────────────────────────────────────────────────────────────
@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: RecipeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    recipe = Recipe(
        name=payload.name,
        owner_id=user.id,
        is_shared=payload.is_shared,
        ingredients=[
            RecipeIngredient(product_id=i.product_id, grams=i.grams)
            for i in payload.ingredients
        ],
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return _load_recipe(db, recipe.id)


# ── PATCH /recipes/{id}/share  — toggle sharing ──────────────────────────────
@router.patch("/{recipe_id}/share", response_model=RecipeOut)
def toggle_share(
    recipe_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if not recipe or recipe.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    recipe.is_shared = not recipe.is_shared
    db.commit()
    return _load_recipe(db, recipe.id)


# ── POST /recipes/{id}/copy  — clone a friend's recipe ───────────────────────
@router.post("/{recipe_id}/copy", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def copy_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    source = _load_recipe(db, recipe_id)
    if not source:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    # Must be shared and from a friend (or own recipe)
    if source.owner_id != user.id:
        friend_ids = _friend_ids(db, user.id)
        if source.owner_id not in friend_ids or not source.is_shared:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Recipe not accessible")

    clone = Recipe(
        name=source.name,
        owner_id=user.id,
        is_shared=False,
        ingredients=[
            RecipeIngredient(product_id=ing.product_id, grams=ing.grams)
            for ing in source.ingredients
        ],
    )
    db.add(clone)
    db.commit()
    return _load_recipe(db, clone.id)


# ── PUT /recipes/{id} ────────────────────────────────────────────────────────
@router.put("/{recipe_id}", response_model=RecipeOut)
def update_recipe(
    recipe_id: int,
    payload: RecipeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if not recipe or recipe.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    recipe.name = payload.name
    recipe.is_shared = payload.is_shared
    for ing in list(recipe.ingredients):
        db.delete(ing)
    recipe.ingredients = [
        RecipeIngredient(product_id=i.product_id, grams=i.grams)
        for i in payload.ingredients
    ]
    db.commit()
    return _load_recipe(db, recipe.id)


# ── DELETE /recipes/{id} ─────────────────────────────────────────────────────
@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    recipe = db.get(Recipe, recipe_id)
    if not recipe or recipe.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    db.delete(recipe)
    db.commit()
