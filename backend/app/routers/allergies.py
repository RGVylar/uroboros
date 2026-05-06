from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, UserAllergy

router = APIRouter(prefix="/allergies", tags=["allergies"])


class AllergyCreate(BaseModel):
    ingredient: str


class AllergyOut(BaseModel):
    id: int
    ingredient: str


@router.get("", response_model=list[AllergyOut])
def list_allergies(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[UserAllergy]:
    """Get all allergies/intolerances for the current user."""
    stmt = select(UserAllergy).where(UserAllergy.user_id == user.id)
    return list(db.scalars(stmt))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AllergyOut)
def add_allergy(
    payload: AllergyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserAllergy:
    """Add a new allergy/intolerance."""
    ingredient = payload.ingredient.lower()

    # Check if already exists
    existing = db.scalar(
        select(UserAllergy).where(
            UserAllergy.user_id == user.id,
            UserAllergy.ingredient == ingredient
        )
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Allergy already exists")

    allergy = UserAllergy(
        user_id=user.id,
        ingredient=ingredient,
    )
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
