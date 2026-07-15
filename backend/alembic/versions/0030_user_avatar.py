"""Preset profile avatar for users

Revision ID: 0030
Revises: 0029
Create Date: 2026-07-15

Stores the chosen preset avatar slug (e.g. "aguacate"). Null means the user
has not picked one and the UI shows the initial disc as before.
"""
from alembic import op
import sqlalchemy as sa

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_id", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_id")
