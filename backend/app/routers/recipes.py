from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func as sqlfunc, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user, require_premium
from app.models import DiaryEntry, Friendship, FriendshipStatus, Recipe, RecipeIngredient, User
from app.models.friendship import FriendshipKind
from app.models.recipe import RecipeScope
from app.routers.downloads import _pick_language
from app.schemas.misc import FrequentRecipeOut, RecipeIn, RecipeOut, ShareScopeIn, SharedRecipeOut
from app.services import recipe_share
from app.services.request_lang import set_request_lang

router = APIRouter(prefix="/recipes", tags=["recipes"])

# /r/<código>: la página pública de una receta. Sin el prefijo /api, como /unete.
page_router = APIRouter(tags=["recipes"])


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


def _card_fields(payload: RecipeIn) -> dict:
    """Campos de la ficha de cocina tal como se guardan: pasos sin espacios
    sobrantes y sin huecos (un paso en blanco no es un paso)."""
    return {
        "steps": [s.strip() for s in payload.steps if s.strip()],
        "servings": payload.servings,
        "prep_minutes": payload.prep_minutes,
        "cook_minutes": payload.cook_minutes,
    }


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
            "total_weight": recipe.total_weight,
            "weight": recipe.weight,
            "steps": recipe.steps,
            "servings": recipe.servings,
            "prep_minutes": recipe.prep_minutes,
            "cook_minutes": recipe.cook_minutes,
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
        total_weight=payload.total_weight,
        **_card_fields(payload),
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
        total_weight=source.total_weight,
        steps=list(source.steps),
        servings=source.servings,
        prep_minutes=source.prep_minutes,
        cook_minutes=source.cook_minutes,
        ingredients=[
            RecipeIngredient(product_id=ing.product_id, grams=ing.grams)
            for ing in source.ingredients
        ],
    )
    db.add(clone)
    db.commit()
    return _load_recipe(db, clone.id)


# ── Enlace público (/r/<código>) ─────────────────────────────────────────────
@router.post("/{recipe_id}/public-link", response_model=RecipeOut)
def create_public_link(
    recipe_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    """Da a la receta su enlace para compartir fuera de la app (o devuelve el
    que ya tenía: compartirla dos veces no debe romper el primer enlace)."""
    recipe = _load_recipe(db, recipe_id)
    if not recipe or recipe.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    if not recipe.public_code:
        while True:
            code = recipe_share.new_code()
            if not db.scalar(select(Recipe.id).where(Recipe.public_code == code)):
                break
        recipe.public_code = code
        db.commit()
    return recipe


@router.delete("/{recipe_id}/public-link", response_model=RecipeOut)
def delete_public_link(
    recipe_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    recipe = _load_recipe(db, recipe_id)
    if not recipe or recipe.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    recipe.public_code = None
    db.commit()
    return recipe


@router.post("/public/{code}/copy", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def copy_public_recipe(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    """"Guardar en mi Uroboros" desde la página pública. Si es mía no la duplica."""
    source_id = db.scalar(select(Recipe.id).where(Recipe.public_code == code))
    source = _load_recipe(db, source_id) if source_id else None
    if not source:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")
    if source.owner_id == user.id:
        return source
    clone = Recipe(
        name=source.name,
        owner_id=user.id,
        share_scope=RecipeScope.none,
        total_weight=source.total_weight,
        steps=list(source.steps),
        servings=source.servings,
        prep_minutes=source.prep_minutes,
        cook_minutes=source.cook_minutes,
        ingredients=[
            RecipeIngredient(product_id=ing.product_id, grams=ing.grams)
            for ing in source.ingredients
        ],
    )
    db.add(clone)
    db.commit()
    return _load_recipe(db, clone.id)


@page_router.get("/r/{code}", response_class=HTMLResponse)
def public_recipe_page(
    code: str,
    accept_language: str | None = Header(default=None),
    lang: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """La receta para quien no está en la app: tarjeta Open Graph, raciones
    ajustables y botón para guardarla. El idioma, como en /unete: ?lang= (lo
    pone quien comparte, porque los crawlers no mandan Accept-Language)."""
    resolved = _pick_language(accept_language, lang)
    # Los genéricos traen su nombre traducido según el idioma de la petición.
    set_request_lang(resolved)
    source_id = db.scalar(select(Recipe.id).where(Recipe.public_code == code))
    recipe = _load_recipe(db, source_id) if source_id else None
    if not recipe:
        return HTMLResponse(recipe_share.render_not_found(resolved), status_code=404)
    owner = db.get(User, recipe.owner_id)
    canonical = f"{recipe_share.APP_URL}/r/{code}" + (f"?lang={resolved}" if lang else "")
    # Poco rato de caché: si quien la compartió la edita, se ve enseguida.
    return HTMLResponse(
        recipe_share.render_page(recipe, owner.name if owner else "", resolved, canonical),
        headers={"Cache-Control": "public, max-age=300", "Vary": "Accept-Language"},
    )


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
    recipe.total_weight = payload.total_weight
    for field, value in _card_fields(payload).items():
        setattr(recipe, field, value)
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
