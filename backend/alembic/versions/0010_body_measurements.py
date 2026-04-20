# -*- coding: utf-8 -*-
"""Body measurement logs

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS body_measurement_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            measurements JSONB NOT NULL,
            logged_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_body_measurement_logs_user_id ON body_measurement_logs (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_body_measurement_logs_logged_at ON body_measurement_logs (logged_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS body_measurement_logs")
