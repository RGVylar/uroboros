from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sqlfunc, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user, require_premium
from app.models import DiaryEntry, Friendship, FriendshipStatus, Recipe, RecipeIngredient, User
from app.models.friendship import FriendshipKind
from app.models.recipe import RecipeScope
from app.schemas.misc import FrequentRecipeOut, RecipeIn, RecipeOut, ShareScopeIn, SharedRecipeOut

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _load_recipe(db: Session, recipe_id: int) -> Recipe:
    stmt = (
        select(Recipe)
        .options(selectinload(Recipe.ingredients).joinedload(RecipeIngredient.product))
        .where(Recipe.id == recipe_id)
    )
    return db.scalars(stmt).first()


def _circles(db: Session, user_id: int) -> tuple[int | None, set[int]]:
    """(partner_id, friend_ids) — friend_ids excludes the partner."""
    partner_id: int | None = None
    friends: set[int] = set()
    stmt = select(Friendship).where(
        or_(Friendship.requester_id == user_id, Friendship.receiver_id == user_id),
        Friendship.status == FriendshipStatus.accepted,
    )
    for f in db.scalars(stmt):
        other = f.receiver_id if f.requester_id == user_id else f.requester_id
        if f.kind is FriendshipKind.partner:
            partner_id = other
        else:
            friends.add(other)
    return partner_id, friends


def _can_see(db: Session, user_id: int, recipe: Recipe) -> bool:
    """Whether `recipe` is shared with this user's circle."""
    if recipe.share_scope is RecipeScope.none:
        return False
    partner_id, friends = _circles(db, user_id)
    if recipe.owner_id == partner_id:
        return True  # partners see both 'partner' and 'friends'
    return recipe.owner_id in friends and recipe.share_scope is RecipeScope.friends


# ── GET /recipes/frequent ────────────────────────────────────────────────────
@router.get("/frequent", response_model=list[FrequentRecipeOut])
def get_frequent_recipes(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Return user's most frequently logged recipes."""
    rows = db.execute(
        select(DiaryEntry.recipe_id, sqlfunc.count(DiaryEntry.id).label("cnt"))
        .where(DiaryEntry.user_id == user.id, DiaryEntry.recipe_id.isnot(None))
        .group_by(DiaryEntry.recipe_id)
        .order_by(sqlfunc.count(DiaryEntry.id).desc())
        .limit(limit)
    ).all()

    result = []
    for recipe_id, count in rows:
        recipe = _load_recipe(db, recipe_id)
        if recipe:
            result.append({"recipe": recipe, "count": count})
    return result


# ── GET /recipes/shared  (must be before /{recipe_id}) ──────────────────────
@router.get("/shared", response_model=list[SharedRecipeOut])
def list_shared_recipes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    partner_id, friend_ids = _circles(db, user.id)
    if not friend_ids and partner_id is None:
        return []

    # Your partner's 'partner' recipes are yours to see; a friend only ever sees
    # what was published to 'friends'.
    visible = []
    if partner_id is not None:
        visible.append(
            (Recipe.owner_id == partner_id)
            & (Recipe.share_scope.in_([RecipeScope.partner, RecipeScope.friends]))
        )
    if friend_ids:
        visible.append(
            Recipe.owner_id.in_(friend_ids) & (Recipe.share_scope == RecipeScope.friends)
        )

    stmt = (
        select(Recipe, User)
        .join(User, Recipe.owner_id == User.id)
        .options(selectinload(Recipe.ingredients).joinedload(RecipeIngredient.product))
        .where(or_(*visible))
        .order_by(Recipe.name)
    )
    results = []
    for recipe, owner in db.execute(stmt):
        results.append({
            "id": recipe.id,
            "name": recipe.name,
            "owner_id": recipe.owner_id,
            "share_scope": recipe.share_scope,
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


# ── GET /recipes/{recipe_id} ─────────────────────────────────────────────────
@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    recipe = _load_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    if recipe.owner_id != user.id and not _can_see(db, user.id, recipe):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    return recipe


FREE_RECIPE_LIMIT = 5


# ── POST /recipes ─────────────────────────────────────────────────────────────
@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: RecipeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    if not user.is_premium_or_trial:
        count = db.scalar(
            select(sqlfunc.count(Recipe.id)).where(Recipe.owner_id == user.id)
        ) or 0
        if count >= FREE_RECIPE_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="premium_required",
            )

    recipe = Recipe(
        name=payload.name,
        owner_id=user.id,
        share_scope=RecipeScope(payload.share_scope),
        ingredients=[
            RecipeIngredient(product_id=i.product_id, grams=i.grams)
            for i in payload.ingredients
        ],
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return _load_recipe(db, recipe.id)


# ── PATCH /recipes/{id}/share  — pick who sees it ────────────────────────────
@router.patch("/{recipe_id}/share", response_model=RecipeOut)
def set_share_scope(
    recipe_id: int,
    payload: ShareScopeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    """Used to be a blind toggle; now the caller says which circle.

    'partner' is allowed with no partner yet — it just means nobody sees it for
    now, and it starts working the day there is one.
    """
    recipe = db.get(Recipe, recipe_id)
    if not recipe or recipe.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    recipe.share_scope = RecipeScope(payload.scope)
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
    # Must be shared with my circle (or be my own)
    if source.owner_id != user.id and not _can_see(db, user.id, source):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Recipe not accessible")

    # The copy is private: someone else's sharing choice isn't mine to inherit.
    clone = Recipe(
        name=source.name,
        owner_id=user.id,
        share_scope=RecipeScope.none,
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
    recipe.share_scope = RecipeScope(payload.share_scope)
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
