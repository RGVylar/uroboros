"""Add shared inventory and shopping list

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-29

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add shared_inventory flag to friendships
    op.execute("ALTER TABLE friendships ADD COLUMN shared_inventory BOOLEAN NOT NULL DEFAULT FALSE")

    # Shared inventory items (belong to a friendship, not a user)
    op.execute("""
        CREATE TABLE shared_inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            friendship_id INTEGER NOT NULL REFERENCES friendships(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity_g REAL NOT NULL DEFAULT 0.0,
            price_per_100g REAL,
            added_by_user_id INTEGER NOT NULL REFERENCES users(id),
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(friendship_id, product_id)
        )
    """)

    # Shared shopping list items
    op.execute("""
        CREATE TABLE shared_shopping_list_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            friendship_id INTEGER NOT NULL REFERENCES friendships(id) ON DELETE CASCADE,
            product_id INTEGER REFERENCES products(id),
            name VARCHAR(255),
            quantity_g REAL,
            is_checked BOOLEAN NOT NULL DEFAULT FALSE,
            source VARCHAR(20) NOT NULL DEFAULT 'manual',
            added_by_user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)


def downgrade() -> None:
    dialect = op.get_context().dialect
    if dialect.name == "postgresql":
        op.execute("ALTER TABLE friendships DROP COLUMN shared_inventory")
        op.execute("DROP TABLE shared_inventory_items")
        op.execute("DROP TABLE shared_shopping_list_items")
