"""composite index on diary_entries(user_id, consumed_at)

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-13
"""
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_diary_entries_user_consumed",
        "diary_entries",
        ["user_id", "consumed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_diary_entries_user_consumed", table_name="diary_entries")
