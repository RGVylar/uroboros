from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, UserGoals
from app.schemas.misc import GoalsIn, GoalsOut

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=GoalsOut)
def get_goals(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserGoals:
    goals = db.get(UserGoals, user.id)
    if not goals:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goals not set")
    return goals


@router.put("", response_model=GoalsOut)
def upsert_goals(
    payload: GoalsIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserGoals:
    goals = db.get(UserGoals, user.id)
    if goals:
        for k, v in payload.model_dump().items():
            setattr(goals, k, v)
    else:
        goals = UserGoals(user_id=user.id, **payload.model_dump())
        db.add(goals)
    db.commit()
    db.refresh(goals)
    return goals
