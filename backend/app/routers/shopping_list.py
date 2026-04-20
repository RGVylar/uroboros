from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models import InventoryItem, User
from app.models.inventory import ShoppingListItem
from app.models.recipe import Recipe, RecipeIngredient
from app.schemas.inventory import (
    ShoppingListItemIn,
    ShoppingListItemOut,
    ShoppingListItemUpdate,
)

router = APIRouter(prefix="/shopping-list", tags=["shopping-list"])


def _to_out(item: ShoppingListItem) -> ShoppingListItemOut:
    return ShoppingListItemOut(
        id=item.id,
        user_id=item.user_id,
        product_id=item.product_id,
        product_name=item.product.name if item.product else item.name,
        product_brand=item.product.brand if item.product else None,
        quantity_g=item.quantity_g,
        is_checked=item.is_checked,
        source=item.source,
        created_at=item.created_at,
    )


@router.get("", response_model=list[ShoppingListItemOut])
def list_shopping(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ShoppingListItemOut]:
    stmt = (
        select(ShoppingListItem)
        .where(ShoppingListItem.user_id == user.id)
        .order_by(ShoppingListItem.is_checked, ShoppingListItem.created_at.desc())
    )
    return [_to_out(i) for i in db.scalars(stmt)]


@router.post("", response_model=ShoppingListItemOut, status_code=status.HTTP_201_CREATED)
def add_to_shopping(
    payload: ShoppingListItemIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ShoppingListItemOut:
    item = ShoppingListItem(
        user_id=user.id,
        product_id=payload.product_id,
        name=payload.name,
        quantity_g=payload.quantity_g,
        source="manual",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.patch("/{item_id}", response_model=ShoppingListItemOut)
def update_shopping_item(
    item_id: int,
    payload: ShoppingListItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ShoppingListItemOut:
    item = db.get(ShoppingListItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    if payload.is_checked is not None:
        item.is_checked = payload.is_checked
    if payload.quantity_g is not None:
        item.quantity_g = payload.quantity_g
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.delete("/checked", status_code=status.HTTP_204_NO_CONTENT)
def clear_checked(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Remove all checked items from the list."""
    stmt = select(ShoppingListItem).where(
        ShoppingListItem.user_id == user.id,
        ShoppingListItem.is_checked == True,  # noqa: E712
    )
    for item in db.scalars(stmt):
        db.delete(item)
    db.commit()


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shopping_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    item = db.get(ShoppingListItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    db.delete(item)
    db.commit()


@router.post(
    "/from-recipe/{recipe_id}",
    response_model=list[ShoppingListItemOut],
    status_code=status.HTTP_201_CREATED,
)
def shopping_from_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ShoppingListItemOut]:
    """
    Compare recipe ingredients with inventory and add missing/insufficient
    quantities to the shopping list. Returns the newly created items.
    """
    stmt = (
        select(Recipe)
        .options(selectinload(Recipe.ingredients).joinedload(RecipeIngredient.product))
        .where(Recipe.id == recipe_id)
    )
    recipe = db.scalars(stmt).first()
    if not recipe:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found")

    # Build inventory map for this user: product_id → quantity_g
    inv_map: dict[int, float] = {
        i.product_id: i.quantity_g
        for i in db.scalars(select(InventoryItem).where(InventoryItem.user_id == user.id))
    }

    created: list[ShoppingListItem] = []
    for ing in recipe.ingredients:
        available = inv_map.get(ing.product_id, 0.0)
        needed = max(0.0, ing.grams - available)
        if needed <= 0:
            continue  # enough in stock

        item = ShoppingListItem(
            user_id=user.id,
            product_id=ing.product_id,
            quantity_g=needed,
            source="recipe",
        )
        db.add(item)
        created.append(item)

    db.commit()
    for item in created:
        db.refresh(item)
    return [_to_out(i) for i in created]


@router.post("/{item_id}/purchase", response_model=ShoppingListItemOut)
def purchase_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ShoppingListItemOut:
    """
    Mark a shopping list item as purchased and add its quantity to the inventory.
    """
    item = db.get(ShoppingListItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")

    item.is_checked = True

    if item.product_id and item.quantity_g:
        existing = db.scalar(
            select(InventoryItem).where(
                InventoryItem.user_id == user.id,
                InventoryItem.product_id == item.product_id,
            )
        )
        if existing:
            existing.quantity_g += item.quantity_g
            existing.updated_at = datetime.now(timezone.utc)
        else:
            db.add(InventoryItem(
                user_id=user.id,
                product_id=item.product_id,
                quantity_g=item.quantity_g,
            ))

    db.commit()
    db.refresh(item)
    return _to_out(item)
