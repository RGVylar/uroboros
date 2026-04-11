"""Add friendships table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type
    friendship_status = sa.Enum(
        "pending", "accepted", "rejected",
        name="friendship_status",
    )
    friendship_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "friendships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("receiver_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "accepted", "rejected", name="friendship_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("can_add_food", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requester_id", "receiver_id", name="uq_friendship_pair"),
    )
    op.create_index("ix_friendships_receiver_id", "friendships", ["receiver_id"])
    op.create_index("ix_friendships_requester_id", "friendships", ["requester_id"])
    op.create_index("ix_friendships_receiver_status", "friendships", ["receiver_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_friendships_receiver_status", table_name="friendships")
    op.drop_index("ix_friendships_requester_id", table_name="friendships")
    op.drop_index("ix_friendships_receiver_id", table_name="friendships")
    op.drop_table("friendships")
    sa.Enum(name="friendship_status").drop(op.get_bind(), checkfirst=True)
