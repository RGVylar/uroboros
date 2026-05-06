"""Add user allergies table

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-06

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name
    if dialect == "postgresql":
        op.execute("""
            CREATE TABLE IF NOT EXISTS user_allergies (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ingredient VARCHAR(255) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """)
        op.execute("CREATE INDEX IF NOT EXISTS ix_user_allergies_user_id ON user_allergies(user_id)")
    else:
        op.execute("""
            CREATE TABLE IF NOT EXISTS user_allergies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ingredient VARCHAR(255) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_allergies")
