"""Add creatine tracking

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE user_goals
            ADD COLUMN IF NOT EXISTS track_creatine BOOLEAN NOT NULL DEFAULT false;

        CREATE TABLE IF NOT EXISTS creatine_logs (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            logged_date DATE NOT NULL,
            CONSTRAINT uq_creatine_user_date UNIQUE (user_id, logged_date)
        );

        CREATE INDEX IF NOT EXISTS ix_creatine_logs_user_id ON creatine_logs(user_id);
        CREATE INDEX IF NOT EXISTS ix_creatine_logs_user_date ON creatine_logs(user_id, logged_date);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS creatine_logs;
        ALTER TABLE user_goals DROP COLUMN IF EXISTS track_creatine;
    """)
