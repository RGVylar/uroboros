from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.models.friendship import Friendship, FriendshipStatus
from app.schemas.auth import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[User]:
    """Users available for the 'also log for' picker (self + allowed friends)."""
    # Case 1: I am requester, receiver gave me permission (can_add_food)
    as_requester = (
        select(Friendship.receiver_id)
        .where(
            Friendship.requester_id == user.id,
            Friendship.status == FriendshipStatus.accepted,
            Friendship.can_add_food.is_(True),
        )
    )
    # Case 2: I am receiver, requester gave me permission (can_add_food_requester)
    as_receiver = (
        select(Friendship.requester_id)
        .where(
            Friendship.receiver_id == user.id,
            Friendship.status == FriendshipStatus.accepted,
            Friendship.can_add_food_requester.is_(True),
        )
    )

    stmt = (
        select(User)
        .where(or_(User.id == user.id, User.id.in_(as_requester), User.id.in_(as_receiver)))
        .order_by(User.name)
    )
    return list(db.scalars(stmt))
