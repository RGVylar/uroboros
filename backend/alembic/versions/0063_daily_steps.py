"""Add daily_steps

Revision ID: 0063
Revises: 0062
Create Date: 2026-10-03

Pasos diarios leídos de Health Connect desde la APK de Android. Una fila por
usuario y día con el total agregado; el móvil reenvía la última semana en cada
sincronización y se sobrescribe (de ahí la restricción única).
"""
from alembic import op
import sqlalchemy as sa

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="health_connect"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "day", name="uq_daily_steps_user_day"),
    )


def downgrade() -> None:
    op.drop_table("daily_steps")
