# -*- coding: utf-8 -*-
"""Add cheat days feature

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add cheat_days_enabled to user_goals
    op.execute(
        "ALTER TABLE user_goals ADD COLUMN IF NOT EXISTS cheat_days_enabled BOOLEAN NOT NULL DEFAULT FALSE"
    )

    # Create cheat_day_logs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS cheat_day_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            used_date DATE NOT NULL,
            CONSTRAINT uq_cheat_day_user_date UNIQUE (user_id, used_date)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cheat_day_logs_user_id ON cheat_day_logs (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cheat_day_logs")
    op.execute("ALTER TABLE user_goals DROP COLUMN IF EXISTS cheat_days_enabled")
