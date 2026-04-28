"""Add supplement tracking

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-28

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_supplements (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name        VARCHAR(100) NOT NULL,
            position    INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS ix_user_supplements_user_id ON user_supplements(user_id);

        CREATE TABLE IF NOT EXISTS supplement_logs (
            id              SERIAL PRIMARY KEY,
            user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            supplement_id   INTEGER NOT NULL REFERENCES user_supplements(id) ON DELETE CASCADE,
            logged_date     DATE NOT NULL,
            CONSTRAINT uq_supp_log UNIQUE (user_id, supplement_id, logged_date)
        );

        CREATE INDEX IF NOT EXISTS ix_supplement_logs_user_date ON supplement_logs(user_id, logged_date);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS supplement_logs;
        DROP TABLE IF EXISTS user_supplements;
    """)
