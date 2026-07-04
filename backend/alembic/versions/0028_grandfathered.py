"""grandfathered flag: launch-cohort users keep full access for life

Revision ID: 0028
Revises: 0027
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column(
        "grandfathered",
        sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    ))
    # Everyone who exists at launch keeps full (premium) access for life,
    # independently of whatever subscription they may buy later. This is what
    # lets us gate features for NEW users without taking anything away from
    # the launch cohort.
    op.execute("UPDATE users SET grandfathered = true")


def downgrade() -> None:
    op.drop_column("users", "grandfathered")
