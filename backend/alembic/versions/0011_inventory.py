# -*- coding: utf-8 -*-
"""Inventory and shopping list

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-20

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── New column on user_goals ─────────────────────────────────────────────
    op.execute(
        "ALTER TABLE user_goals ADD COLUMN IF NOT EXISTS inventory_enabled BOOLEAN NOT NULL DEFAULT false"
    )

    # ── Inventory items ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS inventory_items (
            id            SERIAL PRIMARY KEY,
            user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            product_id    INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            quantity_g    FLOAT   NOT NULL DEFAULT 0,
            price_per_100g FLOAT,
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_inventory_user_product UNIQUE (user_id, product_id)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_items_user_id ON inventory_items (user_id)"
    )

    # ── Shopping list items ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS shopping_list_items (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            product_id  INTEGER REFERENCES products(id) ON DELETE SET NULL,
            name        VARCHAR(255),
            quantity_g  FLOAT,
            is_checked  BOOLEAN NOT NULL DEFAULT false,
            source      VARCHAR(20) NOT NULL DEFAULT 'manual',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_shopping_list_items_user_id ON shopping_list_items (user_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS shopping_list_items")
    op.execute("DROP TABLE IF EXISTS inventory_items")
    op.execute("ALTER TABLE user_goals DROP COLUMN IF EXISTS inventory_enabled")
