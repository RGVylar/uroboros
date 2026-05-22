from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_premium
from app.models import User, UserAllergy
from app.models.friendship import Friendship, FriendshipStatus

router = APIRouter(prefix="/allergies", tags=["allergies"])


class AllergyCreate(BaseModel):
    ingredient: str


class AllergyOut(BaseModel):
    id: int
    ingredient: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[AllergyOut])
def list_allergies(
    user_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[UserAllergy]:
    """Get allergies for the current user or for a friend (if can_add_food)."""
    if user_id is None or user_id == user.id:
        stmt = select(UserAllergy).where(UserAllergy.user_id == user.id)
        return list(db.scalars(stmt))

    # Verify friendship with food-adding permission
    friendship = db.scalar(
        select(Friendship).where(
            Friendship.status == FriendshipStatus.accepted,
            or_(
                # current user is requester and can_add_food
                (Friendship.requester_id == user.id) & (Friendship.receiver_id == user_id) & Friendship.can_add_food.is_(True),
                # current user is receiver and can_add_food_requester
                (Friendship.receiver_id == user.id) & (Friendship.requester_id == user_id) & Friendship.can_add_food_requester.is_(True),
            )
        )
    )
    if not friendship:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No permission to view this user's allergies")

    stmt = select(UserAllergy).where(UserAllergy.user_id == user_id)
    return list(db.scalars(stmt))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AllergyOut)
def add_allergy(
    payload: AllergyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_premium),
) -> UserAllergy:
    """Add a new allergy/intolerance for the current user."""
    ingredient = payload.ingredient.strip().lower()
    if not ingredient:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ingredient cannot be empty")

    existing = db.scalar(
        select(UserAllergy).where(
            UserAllergy.user_id == user.id,
            UserAllergy.ingredient == ingredient
        )
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Allergy already exists")

    allergy = UserAllergy(user_id=user.id, ingredient=ingredient)
    db.add(allergy)
    db.commit()
    db.refresh(allergy)
    return allergy


@router.delete("/{allergy_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_allergy(
    allergy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Remove an allergy/intolerance."""
    allergy = db.get(UserAllergy, allergy_id)
    if not allergy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Allergy not found")
    if allergy.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your allergy")

    db.execute(delete(UserAllergy).where(UserAllergy.id == allergy_id))
    db.commit()
