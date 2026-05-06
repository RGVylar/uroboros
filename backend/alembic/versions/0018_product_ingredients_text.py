"""Add ingredients_text to products

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-06

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS ingredients_text VARCHAR(4096)")


def downgrade() -> None:
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS ingredients_text")
