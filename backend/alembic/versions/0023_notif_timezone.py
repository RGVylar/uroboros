"""Add timezone column to notification_prefs

Revision ID: 0023
Revises: 0022
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_prefs",
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
    )


def downgrade() -> None:
    op.drop_column("notification_prefs", "timezone")
