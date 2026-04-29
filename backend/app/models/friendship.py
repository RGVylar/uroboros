import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FriendshipStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class Friendship(Base):
    """Friend relationship between two users.

    `requester_id` sent the request; `receiver_id` received it.
    Status flows: pending → accepted | rejected.
    `can_add_food` controls whether the friend can log diary entries on
    behalf of this user.
    """

    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint("requester_id", "receiver_id", name="uq_friendship_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[FriendshipStatus] = mapped_column(
        Enum(FriendshipStatus, name="friendship_status"),
        nullable=False,
        default=FriendshipStatus.pending,
        server_default="pending",
    )
    # receiver controls: can the requester add food to the receiver's diary?
    can_add_food: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    # requester controls: can the receiver add food to the requester's diary?
    can_add_food_requester: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Shared household: each side opts in independently; active when both are true
    shared_inventory_requester: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    shared_inventory_receiver: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    @property
    def shared_inventory(self) -> bool:
        return self.shared_inventory_requester and self.shared_inventory_receiver

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    requester: Mapped["User"] = relationship(foreign_keys=[requester_id], lazy="joined")  # noqa: F821
    receiver: Mapped["User"] = relationship(foreign_keys=[receiver_id], lazy="joined")  # noqa: F821
