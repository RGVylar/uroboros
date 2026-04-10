"""add water tracking

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_goals",
        sa.Column("water_ml", sa.Float(), nullable=False, server_default="2000"),
    )
    op.create_table(
        "water_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ml", sa.Float(), nullable=False),
        sa.Column("logged_date", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_water_logs_user_date", "water_logs", ["user_id", "logged_date"])


def downgrade() -> None:
    op.drop_index("ix_water_logs_user_date", table_name="water_logs")
    op.drop_table("water_logs")
    op.drop_column("user_goals", "water_ml")
