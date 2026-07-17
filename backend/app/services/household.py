"""The shared household: one inventory and one shopping list, with your partner.

This lookup used to live copy-pasted in both inventory.py and shopping_list.py,
and it asked "is there an accepted friendship of mine with both shared-inventory
flags on?" — taking whichever row the database happened to return first. That was
fine only as long as nobody had two, which nothing enforced.

Now a household hangs off the partnership, and a user has at most one partner, so
"my shared inventory" has exactly one answer.
"""
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.friendship import Friendship, FriendshipKind, FriendshipStatus


def active_household(db: Session, user_id: int) -> Friendship | None:
    """The partnership whose inventory this user shares, if any.

    None means their inventory is personal — either they have no partner, or one
    of the two hasn't switched sharing on.
    """
    return db.scalar(
        select(Friendship).where(
            or_(Friendship.requester_id == user_id, Friendship.receiver_id == user_id),
            Friendship.status == FriendshipStatus.accepted,
            Friendship.kind == FriendshipKind.partner,
            Friendship.shared_inventory_requester == True,  # noqa: E712
            Friendship.shared_inventory_receiver == True,  # noqa: E712
        )
    )
