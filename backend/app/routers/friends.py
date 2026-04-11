from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.models.friendship import Friendship, FriendshipStatus
from app.schemas.friendship import FriendshipOut, FriendshipRequest, FriendshipUpdate

router = APIRouter(prefix="/friends", tags=["friends"])


def _get_friendship(db: Session, friendship_id: int, user: User) -> Friendship:
    """Return friendship if the current user is a participant."""
    f = db.get(Friendship, friendship_id)
    if not f or (f.requester_id != user.id and f.receiver_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Friendship not found")
    return f


# ---------------------------------------------------------------------------
# GET /friends  — list accepted friends
# ---------------------------------------------------------------------------
@router.get("", response_model=list[FriendshipOut])
def list_friends(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Friendship]:
    stmt = (
        select(Friendship)
        .where(
            or_(Friendship.requester_id == user.id, Friendship.receiver_id == user.id),
            Friendship.status == FriendshipStatus.accepted,
        )
    )
    return list(db.scalars(stmt))


# ---------------------------------------------------------------------------
# GET /friends/pending  — incoming pending requests (receiver = me)
# ---------------------------------------------------------------------------
@router.get("/pending", response_model=list[FriendshipOut])
def list_pending(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Friendship]:
    stmt = select(Friendship).where(
        Friendship.receiver_id == user.id,
        Friendship.status == FriendshipStatus.pending,
    )
    return list(db.scalars(stmt))


# ---------------------------------------------------------------------------
# GET /friends/pending/count  — just the count, for notification badge
# ---------------------------------------------------------------------------
@router.get("/pending/count")
def pending_count(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, int]:
    stmt = select(Friendship).where(
        Friendship.receiver_id == user.id,
        Friendship.status == FriendshipStatus.pending,
    )
    count = len(list(db.scalars(stmt)))
    return {"count": count}


# ---------------------------------------------------------------------------
# POST /friends  — send a friend request by email
# ---------------------------------------------------------------------------
@router.post("", response_model=FriendshipOut, status_code=status.HTTP_201_CREATED)
def send_request(
    payload: FriendshipRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Friendship:
    target = db.scalar(select(User).where(User.email == payload.email))
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ningún usuario con ese email")
    if target.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes añadirte a ti mismo")

    # Check if a relationship already exists in either direction
    existing = db.scalar(
        select(Friendship).where(
            or_(
                (Friendship.requester_id == user.id) & (Friendship.receiver_id == target.id),
                (Friendship.requester_id == target.id) & (Friendship.receiver_id == user.id),
            )
        )
    )
    if existing:
        if existing.status == FriendshipStatus.accepted:
            raise HTTPException(status.HTTP_409_CONFLICT, "Ya sois amigos")
        if existing.status == FriendshipStatus.pending:
            raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una solicitud pendiente")
        # rejected → allow re-requesting: reset it
        existing.status = FriendshipStatus.pending
        existing.requester_id = user.id
        existing.receiver_id = target.id
        db.commit()
        db.refresh(existing)
        return existing

    friendship = Friendship(
        requester_id=user.id,
        receiver_id=target.id,
        status=FriendshipStatus.pending,
        can_add_food=True,
    )
    db.add(friendship)
    db.commit()
    db.refresh(friendship)
    return friendship


# ---------------------------------------------------------------------------
# PATCH /friends/{id}  — accept/reject request or update permissions
# ---------------------------------------------------------------------------
@router.patch("/{friendship_id}", response_model=FriendshipOut)
def update_friendship(
    friendship_id: int,
    payload: FriendshipUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Friendship:
    f = _get_friendship(db, friendship_id, user)

    if payload.status is not None:
        # Only the receiver can accept/reject
        if f.receiver_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el receptor puede aceptar o rechazar")
        f.status = FriendshipStatus(payload.status)

    if payload.can_add_food is not None:
        # Only the receiver controls whether the friend can add food to their diary
        if f.receiver_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el receptor controla los permisos")
        f.can_add_food = payload.can_add_food

    db.commit()
    db.refresh(f)
    return f


# ---------------------------------------------------------------------------
# DELETE /friends/{id}  — remove friendship (either side)
# ---------------------------------------------------------------------------
@router.delete("/{friendship_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_friendship(
    friendship_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    f = _get_friendship(db, friendship_id, user)
    db.delete(f)
    db.commit()
