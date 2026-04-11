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
    created_at: datetime

    class Config:
        from_attributes = True


class FriendshipRequest(BaseModel):
    """Send a friend request by email."""
    email: str


class FriendshipUpdate(BaseModel):
    """Accept/reject a request, or update permissions."""
    status: Literal["accepted", "rejected"] | None = None
    can_add_food: bool | None = None
