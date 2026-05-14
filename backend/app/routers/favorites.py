from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Product, User
from app.models.favorite import UserFavorite
from app.schemas.product import ProductOut

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[ProductOut])
def list_favorites(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Product]:
    """Return all products the user has starred, newest first."""
    rows = db.scalars(
        select(Product)
        .join(UserFavorite, UserFavorite.product_id == Product.id)
        .where(UserFavorite.user_id == user.id)
        .order_by(UserFavorite.created_at.desc())
    ).all()
    return list(rows)


@router.get("/ids", response_model=list[int])
def list_favorite_ids(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[int]:
    """Return just the product IDs the user has starred (cheap for UI checks)."""
    rows = db.scalars(
        select(UserFavorite.product_id).where(UserFavorite.user_id == user.id)
    ).all()
    return list(rows)


@router.post("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_favorite(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    existing = db.scalar(
        select(UserFavorite).where(
            UserFavorite.user_id == user.id,
            UserFavorite.product_id == product_id,
        )
    )
    if existing:
        return  # idempotent — already a favorite

    db.add(UserFavorite(user_id=user.id, product_id=product_id))
    db.commit()


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    row = db.scalar(
        select(UserFavorite).where(
            UserFavorite.user_id == user.id,
            UserFavorite.product_id == product_id,
        )
    )
    if row:
        db.delete(row)
        db.commit()
