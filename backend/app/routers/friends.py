from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, InventoryItem, ShoppingListItem, SharedInventoryItem, SharedShoppingListItem
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
    # Pending friend requests
    friend_requests = len(list(db.scalars(
        select(Friendship).where(
            Friendship.receiver_id == user.id,
            Friendship.status == FriendshipStatus.pending,
        )
    )))

    # Pending inventory share: other side activated their flag, mine is still off
    # Case: I am receiver, requester activated theirs but I haven't
    inv_as_receiver = len(list(db.scalars(
        select(Friendship).where(
            Friendship.receiver_id == user.id,
            Friendship.status == FriendshipStatus.accepted,
            Friendship.shared_inventory_requester == True,  # noqa: E712
            Friendship.shared_inventory_receiver == False,  # noqa: E712
        )
    )))
    # Case: I am requester, receiver activated theirs but I haven't
    inv_as_requester = len(list(db.scalars(
        select(Friendship).where(
            Friendship.requester_id == user.id,
            Friendship.status == FriendshipStatus.accepted,
            Friendship.shared_inventory_receiver == True,  # noqa: E712
            Friendship.shared_inventory_requester == False,  # noqa: E712
        )
    )))

    return {"count": friend_requests + inv_as_receiver + inv_as_requester}


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
# Helper: migrate personal inventories → shared on activation
# ---------------------------------------------------------------------------

def _migrate_to_shared(db: Session, f: Friendship) -> None:
    """Copy both users' personal inventory + shopping list into the shared tables."""
    user_ids = [f.requester_id, f.receiver_id]

    # ── Inventory ────────────────────────────────────────────────────────────
    personal_items = list(db.scalars(
        select(InventoryItem).where(InventoryItem.user_id.in_(user_ids))
    ))
    # Merge by product_id: sum quantities
    merged: dict[int, dict] = {}
    for item in personal_items:
        if item.product_id not in merged:
            merged[item.product_id] = {
                "quantity_g": item.quantity_g,
                "price_per_100g": item.price_per_100g,
                "added_by_user_id": item.user_id,
            }
        else:
            merged[item.product_id]["quantity_g"] += item.quantity_g
            # Keep most recent price if available
            if item.price_per_100g is not None:
                merged[item.product_id]["price_per_100g"] = item.price_per_100g

    for product_id, data in merged.items():
        # Skip if already exists in shared (idempotent)
        existing = db.scalar(
            select(SharedInventoryItem).where(
                SharedInventoryItem.friendship_id == f.id,
                SharedInventoryItem.product_id == product_id,
            )
        )
        if not existing:
            db.add(SharedInventoryItem(
                friendship_id=f.id,
                product_id=product_id,
                quantity_g=data["quantity_g"],
                price_per_100g=data["price_per_100g"],
                added_by_user_id=data["added_by_user_id"],
            ))

    # ── Shopping list ─────────────────────────────────────────────────────────
    personal_shopping = list(db.scalars(
        select(ShoppingListItem).where(ShoppingListItem.user_id.in_(user_ids))
    ))
    for item in personal_shopping:
        db.add(SharedShoppingListItem(
            friendship_id=f.id,
            product_id=item.product_id,
            name=item.name,
            quantity_g=item.quantity_g,
            is_checked=item.is_checked,
            source=item.source,
            added_by_user_id=item.user_id,
        ))

    db.flush()


def _split_from_shared(db: Session, f: Friendship) -> None:
    """On deactivation: copy shared items back to each user's personal inventory."""
    shared_items = list(db.scalars(
        select(SharedInventoryItem).where(SharedInventoryItem.friendship_id == f.id)
    ))
    for item in shared_items:
        # Give the item to whoever added it; if conflict, give to requester
        owner_id = item.added_by_user_id
        existing = db.scalar(
            select(InventoryItem).where(
                InventoryItem.user_id == owner_id,
                InventoryItem.product_id == item.product_id,
            )
        )
        if existing:
            existing.quantity_g += item.quantity_g
        else:
            db.add(InventoryItem(
                user_id=owner_id,
                product_id=item.product_id,
                quantity_g=item.quantity_g,
                price_per_100g=item.price_per_100g,
            ))
        db.delete(item)

    shared_shopping = list(db.scalars(
        select(SharedShoppingListItem).where(SharedShoppingListItem.friendship_id == f.id)
    ))
    for item in shared_shopping:
        db.add(ShoppingListItem(
            user_id=item.added_by_user_id,
            product_id=item.product_id,
            name=item.name,
            quantity_g=item.quantity_g,
            is_checked=item.is_checked,
            source=item.source,
        ))
        db.delete(item)

    db.flush()


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
        # Receiver controls whether requester can add to receiver's diary
        if f.receiver_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el receptor controla este permiso")
        f.can_add_food = payload.can_add_food

    if payload.can_add_food_requester is not None:
        # Requester controls whether receiver can add to requester's diary
        if f.requester_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el solicitante controla este permiso")
        f.can_add_food_requester = payload.can_add_food_requester

    # Double-flag shared inventory: each side opts in independently
    if payload.shared_inventory_requester is not None:
        if f.requester_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el solicitante puede cambiar su flag")
        if f.status != FriendshipStatus.accepted:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La amistad debe estar aceptada")
        was_shared = f.shared_inventory
        f.shared_inventory_requester = payload.shared_inventory_requester
        now_shared = f.shared_inventory
        if now_shared and not was_shared:
            _migrate_to_shared(db, f)
        elif not now_shared and was_shared:
            _split_from_shared(db, f)

    if payload.shared_inventory_receiver is not None:
        if f.receiver_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el receptor puede cambiar su flag")
        if f.status != FriendshipStatus.accepted:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La amistad debe estar aceptada")
        was_shared = f.shared_inventory
        f.shared_inventory_receiver = payload.shared_inventory_receiver
        now_shared = f.shared_inventory
        if now_shared and not was_shared:
            _migrate_to_shared(db, f)
        elif not now_shared and was_shared:
            _split_from_shared(db, f)

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
