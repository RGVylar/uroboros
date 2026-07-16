"""Weekly adherence snapshot for the anonymous percentile

Revision ID: 0034
Revises: 0033
Create Date: 2026-07-16

One row per user per ISO week, refreshed by a scheduler job, so the "top X% de
uroboros esta semana" stat is a couple of row reads instead of recomputing the
whole population on every view.
"""
from alembic import op
import sqlalchemy as sa

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weekly_adherence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("week_start", sa.Date(), nullable=False, index=True),
        sa.Column("pct", sa.Integer(), nullable=False),
        sa.Column("counted", sa.Integer(), nullable=False),
        sa.Column(
            "computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "week_start", name="uq_weekly_adherence_user_week"),
    )


def downgrade() -> None:
    op.drop_table("weekly_adherence")
