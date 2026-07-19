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
    # IF NOT EXISTS: the app also creates these via Base.metadata.create_all()
    # on startup, so the index may already exist when the migration runs.
    # Valid on both PostgreSQL and SQLite.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_water_logs_user_date "
        "ON water_logs (user_id, logged_date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_supplements_user_id "
        "ON user_supplements (user_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_supplements_user_id")
    op.execute("DROP INDEX IF EXISTS ix_water_logs_user_date")
