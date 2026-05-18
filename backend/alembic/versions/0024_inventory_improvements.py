"""Inventory improvements: location, unit, quantity_base + InventoryLog + UnitConversion

Revision ID: 0024
Revises: 0023
Create Date: 2026-05-19

Changes:
- Add `location`, `unit`, `quantity_base` columns to `inventory_items` and `shared_inventory_items`
- Add `unit` column to `shopping_list_items` and `shared_shopping_list_items`
- Create `inventory_logs` table for audit (purchase/consume/adjust history)
- Create `unit_conversions` table (g -> ml -> unit conversions, optionally per-product)
- Seed default unit conversions (g→g=1, ml→g=1, unit→g=100 placeholder)
"""

from alembic import op
import sqlalchemy as sa

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extend inventory_items ──────────────────────────────────────────
    op.add_column(
        "inventory_items",
        sa.Column("location", sa.String(20), nullable=False, server_default="pantry"),
    )
    op.add_column(
        "inventory_items",
        sa.Column("unit", sa.String(20), nullable=False, server_default="g"),
    )
    op.add_column(
        "inventory_items",
        sa.Column("quantity_base", sa.Float(), nullable=False, server_default="0.0"),
    )
    # Backfill quantity_base = quantity_g for existing rows
    op.execute("UPDATE inventory_items SET quantity_base = quantity_g WHERE quantity_base = 0.0")

    # ── 2. Extend shared_inventory_items ───────────────────────────────────
    op.add_column(
        "shared_inventory_items",
        sa.Column("location", sa.String(20), nullable=False, server_default="pantry"),
    )
    op.add_column(
        "shared_inventory_items",
        sa.Column("unit", sa.String(20), nullable=False, server_default="g"),
    )
    op.add_column(
        "shared_inventory_items",
        sa.Column("quantity_base", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.execute(
        "UPDATE shared_inventory_items SET quantity_base = quantity_g WHERE quantity_base = 0.0"
    )

    # ── 3. Extend shopping_list_items with unit ────────────────────────────
    op.add_column(
        "shopping_list_items",
        sa.Column("unit", sa.String(20), nullable=False, server_default="g"),
    )
    op.add_column(
        "shared_shopping_list_items",
        sa.Column("unit", sa.String(20), nullable=False, server_default="g"),
    )

    # ── 4. Create inventory_logs ───────────────────────────────────────────
    op.create_table(
        "inventory_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("inventory_items.id", ondelete="CASCADE"),
            nullable=True,  # nullable: item might be deleted but we want to keep history
            index=True,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id"),
            nullable=True,  # nullable in case product was removed
        ),
        sa.Column("quantity_change", sa.Float(), nullable=False),
        # positive = purchase / add, negative = consume / remove
        sa.Column("unit", sa.String(20), nullable=False, server_default="g"),
        sa.Column("quantity_base_change", sa.Float(), nullable=False),
        # always in g, computed from quantity_change * conversion factor
        sa.Column("log_type", sa.String(20), nullable=False),
        # 'purchase' | 'consume' | 'adjust'
        sa.Column("price_per_unit", sa.Float(), nullable=True),
        # snapshot of the price at the time of the log entry (for cost analytics)
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_inventory_logs_user_created",
        "inventory_logs",
        ["user_id", "created_at"],
    )

    # ── 5. Create unit_conversions ─────────────────────────────────────────
    op.create_table(
        "unit_conversions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_unit", sa.String(20), nullable=False),
        sa.Column("to_unit", sa.String(20), nullable=False, server_default="g"),
        sa.Column("factor", sa.Float(), nullable=False),
        # 1 from_unit = factor * to_unit (in grams)
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=True,  # NULL = global conversion
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_unit_conversions_from_to_product",
        "unit_conversions",
        ["from_unit", "to_unit", "product_id"],
    )

    # ── 6. Seed default global conversions ─────────────────────────────────
    op.execute(
        """
        INSERT INTO unit_conversions (from_unit, to_unit, factor, product_id)
        VALUES
            ('g', 'g', 1.0, NULL),
            ('ml', 'g', 1.0, NULL),
            ('unit', 'g', 100.0, NULL)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_unit_conversions_from_to_product", table_name="unit_conversions")
    op.drop_table("unit_conversions")

    op.drop_index("ix_inventory_logs_user_created", table_name="inventory_logs")
    op.drop_table("inventory_logs")

    op.drop_column("shared_shopping_list_items", "unit")
    op.drop_column("shopping_list_items", "unit")

    op.drop_column("shared_inventory_items", "quantity_base")
    op.drop_column("shared_inventory_items", "unit")
    op.drop_column("shared_inventory_items", "location")

    op.drop_column("inventory_items", "quantity_base")
    op.drop_column("inventory_items", "unit")
    op.drop_column("inventory_items", "location")
