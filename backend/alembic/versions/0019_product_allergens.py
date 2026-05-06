"""Add allergens to products

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-06

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS allergens JSON")


def downgrade() -> None:
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS allergens")
