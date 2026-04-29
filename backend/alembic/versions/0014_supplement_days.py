"""Add days_of_week to user_supplements

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-29

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE user_supplements ADD COLUMN days_of_week_json TEXT DEFAULT NULL")


def downgrade() -> None:
    # SQLite doesn't support DROP COLUMN easily; for PG:
    dialect = op.get_context().dialect
    if dialect.name == "postgresql":
        op.execute("ALTER TABLE user_supplements DROP COLUMN days_of_week_json")
