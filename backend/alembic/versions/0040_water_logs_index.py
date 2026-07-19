"""Composite index on water_logs(user_id, logged_date)

Revision ID: 0040
Revises: 0039
Create Date: 2026-07-19

/water/day filters by (user_id, logged_date) on every dashboard/history load and
water_logs had no index at all, so it was a full scan that grows with every glass
logged by every user. Also indexes user_supplements.user_id (small table, cheap
to add while we're here).
"""
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_water_logs_user_date",
        "water_logs",
        ["user_id", "logged_date"],
    )
    op.create_index(
        "ix_user_supplements_user_id",
        "user_supplements",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_supplements_user_id", table_name="user_supplements")
    op.drop_index("ix_water_logs_user_date", table_name="water_logs")
