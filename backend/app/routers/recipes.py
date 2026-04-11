from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models import Recipe, RecipeIngredient, User
from app.schemas.misc import RecipeIn, RecipeOut

router = APIRouter(prefix="/recipes", tags=["recipes"])


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


@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: RecipeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Recipe:
    recipe = Recipe(
        name=payload.name,
        owner_id=user.id,
        ingredients=[
            RecipeIngredient(product_id=i.product_id, grams=i.grams)
            for i in payload.ingredients
        ],
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


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
    # Replace all ingredients
    for ing in list(recipe.ingredients):
        db.delete(ing)
    recipe.ingredients = [
        RecipeIngredient(product_id=i.product_id, grams=i.grams)
        for i in payload.ingredients
    ]
    db.commit()
    db.refresh(recipe)
    # Reload with products
    stmt = (
        select(Recipe)
        .options(selectinload(Recipe.ingredients).joinedload(RecipeIngredient.product))
        .where(Recipe.id == recipe_id)
    )
    return db.scalars(stmt).first()


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
