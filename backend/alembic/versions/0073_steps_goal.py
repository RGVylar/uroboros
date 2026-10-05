"""Add user_goals.steps_goal

Revision ID: 0073
Revises: 0072
Create Date: 2026-10-05

Objetivo diario de pasos para la barra de la tarjeta de pasos del diario.
"""
from alembic import op
import sqlalchemy as sa

revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_goals", sa.Column("steps_goal", sa.Integer(), nullable=False, server_default="8000"))


def downgrade() -> None:
    op.drop_column("user_goals", "steps_goal")
