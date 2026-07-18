from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, InventoryItem, ShoppingListItem, SharedInventoryItem, SharedShoppingListItem
from app.models.friendship import Friendship, FriendshipKind, FriendshipStatus
from app.schemas.friendship import FriendshipOut, FriendshipRequest, FriendshipUpdate

router = APIRouter(prefix="/friends", tags=["friends"])


def _get_friendship(db: Session, friendship_id: int, user: User) -> Friendship:
    """Return friendship if the current user is a participant."""
    f = db.get(Friendship, friendship_id)
    if not f or (f.requester_id != user.id and f.receiver_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Friendship not found")
    return f


def _partner_of(db: Session, user_id: int, exclude_id: int | None = None) -> Friendship | None:
    """The user's accepted partnership, if they have one.

    This is what actually enforces "one partner per user": the partial unique
    indexes catch being the requester of two partnerships or the receiver of
    two, but not the requester of one and the receiver of another — a unique
    index gets one entry per row, and a row has two participants.
    """
    stmt = select(Friendship).where(
        or_(Friendship.requester_id == user_id, Friendship.receiver_id == user_id),
        Friendship.status == FriendshipStatus.accepted,
        Friendship.kind == FriendshipKind.partner,
    )
    if exclude_id is not None:
        stmt = stmt.where(Friendship.id != exclude_id)
    return db.scalar(stmt)


def _reject_if_taken(db: Session, me_id: int, other_id: int, exclude_id: int | None = None) -> None:
    """409 if either side already has a partner.

    Only names my own partner back to me: who someone else is paired with is
    their business, not something to leak in an error message.
    """
    mine = _partner_of(db, me_id, exclude_id=exclude_id)
    if mine:
        their = mine.receiver if mine.requester_id == me_id else mine.requester
        raise HTTPException(status.HTTP_409_CONFLICT, f"Ya tienes pareja ({their.name})")
    if _partner_of(db, other_id, exclude_id=exclude_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Esa persona ya tiene pareja")


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
        .order_by(Friendship.kind.desc(), Friendship.created_at)  # partner first, then oldest
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

    kind = FriendshipKind(payload.kind)
    if kind is FriendshipKind.partner:
        _reject_if_taken(db, user.id, target.id)

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
        existing.kind = kind
        existing.requester_id = user.id
        existing.receiver_id = target.id
        db.commit()
        db.refresh(existing)
        return existing

    # can_add_food starts off. It used to default to true, which meant every
    # request you sent silently handed you write access to the other person's
    # diary the moment they accepted — nobody ever asked for that.
    friendship = Friendship(
        requester_id=user.id,
        receiver_id=target.id,
        status=FriendshipStatus.pending,
        kind=kind,
        can_add_food=False,
    )
    db.add(friendship)
    db.commit()
    db.refresh(friendship)
    return friendship


# ---------------------------------------------------------------------------
# Helper: migrate personal inventories → shared on activation
# ---------------------------------------------------------------------------

def _migrate_to_shared(db: Session, f: Friendship) -> None:
    """Move both users' personal inventory + shopping list into the shared tables.

    The personal rows are deleted once absorbed. They used to be left behind:
    invisible while sharing (every read goes to the shared tables), but
    `_split_from_shared` adds the shared stock back *on top* of them, so turning
    sharing off handed you doubled quantities.
    """
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

    for item in personal_items:
        db.delete(item)

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
        db.delete(item)

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
    other_id = f.receiver_id if f.requester_id == user.id else f.requester_id

    # Kind is handled before status on purpose: "I accept, but only as a friend"
    # arrives as {status: accepted, kind: friend} in one request, and this branch
    # has to still see it as pending to tell it apart from a demotion.
    if payload.kind is not None:
        requested = FriendshipKind(payload.kind)

        if f.status == FriendshipStatus.pending:
            if f.receiver_id != user.id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN, "Solo quien recibe la solicitud elige cómo aceptarla"
                )
            if requested is FriendshipKind.partner and f.kind is not FriendshipKind.partner:
                # Accepting can only lower the kind. Deciding on your own that
                # someone is your partner is exactly what we're fixing.
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "No puedes aceptar como pareja lo que no se propuso"
                )
            f.kind = requested

        elif f.status == FriendshipStatus.accepted:
            if requested is FriendshipKind.partner:
                if f.kind is not FriendshipKind.partner:
                    _reject_if_taken(db, user.id, other_id, exclude_id=f.id)
                    if f.partner_proposed_by is None:
                        f.partner_proposed_by = user.id  # proposed, waiting on them
                    elif f.partner_proposed_by != user.id:
                        f.kind = FriendshipKind.partner  # both asked → sealed
                        f.partner_proposed_by = None
            else:
                # Demotion is unilateral: you don't need the other side's blessing
                # to stop being someone's partner. The household splits back, and
                # the partner-only permissions (diary access) reset too.
                if f.kind is FriendshipKind.partner:
                    if f.shared_inventory:
                        _split_from_shared(db, f)
                    f.shared_inventory_requester = False
                    f.shared_inventory_receiver = False
                    f.can_add_food = False
                    f.can_add_food_requester = False
                    f.kind = FriendshipKind.friend
                f.partner_proposed_by = None

    if payload.status is not None:
        # Only the receiver can accept/reject
        if f.receiver_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el receptor puede aceptar o rechazar")
        if payload.status == "accepted" and f.kind is FriendshipKind.partner:
            _reject_if_taken(db, f.receiver_id, f.requester_id, exclude_id=f.id)
        f.status = FriendshipStatus(payload.status)

    if payload.can_add_food is not None:
        # Receiver controls whether requester can add to receiver's diary.
        # Partners only: writing in someone's diary is a couple thing.
        if f.receiver_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el receptor controla este permiso")
        if f.kind is not FriendshipKind.partner:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo tu pareja puede añadir a tu diario")
        f.can_add_food = payload.can_add_food

    if payload.can_add_food_requester is not None:
        # Requester controls whether receiver can add to requester's diary
        if f.requester_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el solicitante controla este permiso")
        if f.kind is not FriendshipKind.partner:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo tu pareja puede añadir a tu diario")
        f.can_add_food_requester = payload.can_add_food_requester

    # Double-flag shared inventory: each side opts in independently. Only for
    # partners — a household is a 1:1 thing, and the whole reason the "which
    # shared inventory is mine?" lookup used to be ambiguous was that nothing
    # said so.
    if payload.shared_inventory_requester is not None:
        if f.requester_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el solicitante puede cambiar su flag")
        if f.status != FriendshipStatus.accepted:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La amistad debe estar aceptada")
        if f.kind is not FriendshipKind.partner:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "La despensa compartida es solo con tu pareja"
            )
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
        if f.kind is not FriendshipKind.partner:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "La despensa compartida es solo con tu pareja"
            )
        was_shared = f.shared_inventory
        f.shared_inventory_receiver = payload.shared_inventory_receiver
        now_shared = f.shared_inventory
        if now_shared and not was_shared:
            _migrate_to_shared(db, f)
        elif not now_shared and was_shared:
            _split_from_shared(db, f)

    # Duel opt-in — double flag, each side owns their own (no data migration).
    if payload.duel_opt_in_requester is not None:
        if f.requester_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el solicitante puede cambiar su flag")
        if f.status != FriendshipStatus.accepted:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La amistad debe estar aceptada")
        f.duel_opt_in_requester = payload.duel_opt_in_requester

    if payload.duel_opt_in_receiver is not None:
        if f.receiver_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el receptor puede cambiar su flag")
        if f.status != FriendshipStatus.accepted:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La amistad debe estar aceptada")
        f.duel_opt_in_receiver = payload.duel_opt_in_receiver

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
    """Remove the relationship, giving the household back first.

    shared_inventory_items and shared_shopping_list_items are ON DELETE CASCADE
    from friendships, so deleting the row on its own doesn't split the household
    — it deletes it, and both people lose the stock. Split first, then drop.
    """
    f = _get_friendship(db, friendship_id, user)
    if f.shared_inventory:
        _split_from_shared(db, f)
    db.delete(f)
    db.commit()
