import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, UniqueConstraint, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FriendshipStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class FriendshipKind(str, enum.Enum):
    """What kind of relationship this is.

    `partner` unlocks the household features (shared inventory + shopping list)
    and is capped at one per user; `friend` gets recipes and the duel.
    """

    friend = "friend"
    partner = "partner"


class Friendship(Base):
    """Friend relationship between two users.

    `requester_id` sent the request; `receiver_id` received it.
    Status flows: pending → accepted | rejected.
    `kind` is what the relationship *is*; the flags below are what each side has
    switched on within it.
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
    kind: Mapped[FriendshipKind] = mapped_column(
        Enum(FriendshipKind, name="friendship_kind"),
        nullable=False,
        default=FriendshipKind.friend,
        server_default="friend",
    )
    # Promoting an existing friendship to partner needs both sides, like every
    # other shared feature. One nullable column says it better than two flags:
    # who proposed. Cleared once the other side agrees (or backs out).
    partner_proposed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    # Every flag below is server_default=false() rather than the string "false".
    # A Python string becomes a quoted SQL literal: Postgres casts DEFAULT 'false'
    # to boolean and it works, but SQLite stores the *text* "false", which reads
    # back as True. false() renders the right literal for each dialect.
    #
    # receiver controls: can the requester add food to the receiver's diary?
    can_add_food: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    # requester controls: can the receiver add food to the requester's diary?
    can_add_food_requester: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    # Shared household: each side opts in independently; active when both are true
    shared_inventory_requester: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    shared_inventory_receiver: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())

    # Weekly adherence duel: same double opt-in — only the % is shared, never the
    # diary, and it's off until both sides agree.
    duel_opt_in_requester: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    duel_opt_in_receiver: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())

    @property
    def shared_inventory(self) -> bool:
        return self.shared_inventory_requester and self.shared_inventory_receiver

    @property
    def duel_active(self) -> bool:
        return self.duel_opt_in_requester and self.duel_opt_in_receiver

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    requester: Mapped["User"] = relationship(foreign_keys=[requester_id], lazy="joined")  # noqa: F821
    receiver: Mapped["User"] = relationship(foreign_keys=[receiver_id], lazy="joined")  # noqa: F821
