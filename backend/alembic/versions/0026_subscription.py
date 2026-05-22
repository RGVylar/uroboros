"""subscription fields on users

Revision ID: 0026
Revises: 0025
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column(
        "subscription_status",
        sa.String(20),
        nullable=False,
        server_default="free",
    ))
    op.add_column("users", sa.Column(
        "trial_started_at",
        sa.DateTime(timezone=True),
        nullable=True,
    ))
    op.add_column("users", sa.Column(
        "subscription_expires_at",
        sa.DateTime(timezone=True),
        nullable=True,
    ))

    # Existing users → premium (grandfathered)
    op.execute("UPDATE users SET subscription_status = 'premium'")


def downgrade() -> None:
    op.drop_column("users", "subscription_expires_at")
    op.drop_column("users", "trial_started_at")
    op.drop_column("users", "subscription_status")
