"""Add macro_adjust_mode to user_goals

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-06

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE user_goals ADD COLUMN IF NOT EXISTS "
        "macro_adjust_mode VARCHAR(20) NOT NULL DEFAULT 'off'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE user_goals DROP COLUMN IF EXISTS macro_adjust_mode")
