from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

from app.models.friendship import FriendshipStatus


class UserMinimal(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class FriendshipOut(BaseModel):
    id: int
    requester: UserMinimal
    receiver: UserMinimal
    status: FriendshipStatus
    can_add_food: bool
    can_add_food_requester: bool
    shared_inventory_requester: bool
    shared_inventory_receiver: bool
    shared_inventory: bool  # computed: both true
    created_at: datetime

    class Config:
        from_attributes = True


class FriendshipRequest(BaseModel):
    """Send a friend request by email."""
    email: str


class FriendshipUpdate(BaseModel):
    """Accept/reject a request, or update permissions."""
    status: Literal["accepted", "rejected"] | None = None
    can_add_food: bool | None = None           # receiver controls
    can_add_food_requester: bool | None = None  # requester controls
    # Each side opts in independently
    shared_inventory_requester: bool | None = None
    shared_inventory_receiver: bool | None = None
