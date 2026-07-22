from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

from app.models.friendship import FriendshipKind, FriendshipStatus


class UserMinimal(BaseModel):
    id: int
    name: str
    email: str
    avatar_id: str | None = None
    identity_hue: int | None = None

    class Config:
        from_attributes = True


class FriendshipOut(BaseModel):
    id: int
    requester: UserMinimal
    receiver: UserMinimal
    status: FriendshipStatus
    kind: FriendshipKind
    partner_proposed_by: int | None = None
    can_add_food: bool
    can_add_food_requester: bool
    shared_inventory_requester: bool
    shared_inventory_receiver: bool
    shared_inventory: bool  # computed: both true
    duel_opt_in_requester: bool
    duel_opt_in_receiver: bool
    duel_active: bool  # computed: both true
    created_at: datetime

    class Config:
        from_attributes = True


class FriendshipRequest(BaseModel):
    """Send a friend request by email."""
    email: str
    kind: Literal["friend", "partner"] = "friend"


class FriendshipUpdate(BaseModel):
    """Accept/reject a request, or update permissions.

    `kind` does double duty on an accepted friendship: asking for "partner"
    proposes it (and seals it once the other side asks too), asking for "friend"
    steps back down. On a pending request it can only lower what was proposed.
    """
    status: Literal["accepted", "rejected"] | None = None
    kind: Literal["friend", "partner"] | None = None
    can_add_food: bool | None = None           # receiver controls
    can_add_food_requester: bool | None = None  # requester controls
    # Each side opts in independently
    shared_inventory_requester: bool | None = None
    shared_inventory_receiver: bool | None = None
    duel_opt_in_requester: bool | None = None
    duel_opt_in_receiver: bool | None = None
