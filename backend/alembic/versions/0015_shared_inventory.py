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
    dialect = op.get_context().dialect.name

    # Add double-flag shared inventory to friendships
    op.execute("ALTER TABLE friendships ADD COLUMN IF NOT EXISTS shared_inventory_requester BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE friendships ADD COLUMN IF NOT EXISTS shared_inventory_receiver BOOLEAN NOT NULL DEFAULT FALSE")
    # Add bidirectional can_add_food
    op.execute("ALTER TABLE friendships ADD COLUMN IF NOT EXISTS can_add_food_requester BOOLEAN NOT NULL DEFAULT FALSE")

    # Shared inventory items (belong to a friendship, not a user)
    if dialect == "postgresql":
        op.execute("""
            CREATE TABLE IF NOT EXISTS shared_inventory_items (
                id SERIAL PRIMARY KEY,
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
        op.execute("""
            CREATE TABLE IF NOT EXISTS shared_shopping_list_items (
                id SERIAL PRIMARY KEY,
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
    else:
        # SQLite
        op.execute("""
            CREATE TABLE IF NOT EXISTS shared_inventory_items (
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
        op.execute("""
            CREATE TABLE IF NOT EXISTS shared_shopping_list_items (
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
    op.execute("DROP TABLE IF EXISTS shared_shopping_list_items")
    op.execute("DROP TABLE IF EXISTS shared_inventory_items")
    op.execute("ALTER TABLE friendships DROP COLUMN IF EXISTS shared_inventory_requester")
    op.execute("ALTER TABLE friendships DROP COLUMN IF EXISTS shared_inventory_receiver")
    op.execute("ALTER TABLE friendships DROP COLUMN IF EXISTS can_add_food_requester")
