from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, UserGoals
from app.models.friendship import Friendship, FriendshipKind, FriendshipStatus
from app.schemas.misc import GoalsIn, GoalsOut

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=GoalsOut)
def get_goals(
    user_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserGoals:
    """Get the current user's goals, or a partner's (if can_add_food).

    Same rule as allergies: seeing someone's goals rides on the diary
    permission, both partner-only — you only need someone's goals to make
    sense of the totals you see when browsing their day.
    """
    target_id = user.id
    if user_id is not None and user_id != user.id:
        friendship = db.scalar(
            select(Friendship).where(
                Friendship.status == FriendshipStatus.accepted,
                Friendship.kind == FriendshipKind.partner,
                or_(
                    (Friendship.requester_id == user.id) & (Friendship.receiver_id == user_id) & Friendship.can_add_food.is_(True),
                    (Friendship.receiver_id == user.id) & (Friendship.requester_id == user_id) & Friendship.can_add_food_requester.is_(True),
                )
            )
        )
        if not friendship:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No permission to view this user's goals")
        target_id = user_id

    goals = db.get(UserGoals, target_id)
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
