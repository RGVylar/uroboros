"""add meal_type to diary entries

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE meal_type AS ENUM ('breakfast', 'lunch', 'dinner', 'snack')")
    op.add_column(
        "diary_entries",
        sa.Column(
            "meal_type",
            sa.Enum("breakfast", "lunch", "dinner", "snack", name="meal_type"),
            nullable=False,
            server_default="snack",
        ),
    )


def downgrade() -> None:
    op.drop_column("diary_entries", "meal_type")
    op.execute("DROP TYPE meal_type")
