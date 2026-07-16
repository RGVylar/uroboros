"""Weekly adherence duel opt-in

Revision ID: 0032
Revises: 0031
Create Date: 2026-07-16

Double opt-in flags on friendships for the weekly adherence duel, mirroring the
shared-inventory pattern: the duel is only active when both sides have opted in.
"""
from alembic import op
import sqlalchemy as sa

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "friendships",
        sa.Column("duel_opt_in_requester", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "friendships",
        sa.Column("duel_opt_in_receiver", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("friendships", "duel_opt_in_receiver")
    op.drop_column("friendships", "duel_opt_in_requester")
