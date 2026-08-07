"""Add product_aliases, receipt_imports and inventory_logs.receipt_import_id

Revision ID: 0052
Revises: 0051
Create Date: 2026-08-07

Las dos tablas del escaneo de tickets.

`product_aliases` es la memoria de "lo que pone el ticket ↔ qué producto es".
Un ticket no dice `Leche semidesnatada`, dice `LECHE SEM DESN 1L`; ningún
emparejador genérico acierta eso, pero recordarlo sí funciona.

Ojo a los **dos índices únicos parciales** en vez de uno: `user_id` es nullable
(nulo = alias global) y en SQL NULL != NULL, así que un único constraint dejaría
duplicar los globales sin protestar.

`receipt_imports` + `inventory_logs.receipt_import_id` existen para poder
deshacer una importación entera de un toque. Los logs de compra ya existían;
solo les faltaba saber de qué tanda venían.
"""
import sqlalchemy as sa
from alembic import op

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("store", sa.String(64), nullable=False, server_default=""),
        sa.Column("raw_text_norm", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="product"),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("times_seen", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_product_aliases_user_id", "product_aliases", ["user_id"])
    op.create_index("ix_alias_lookup", "product_aliases", ["raw_text_norm", "store"])
    op.create_index(
        "uq_alias_user",
        "product_aliases",
        ["user_id", "store", "raw_text_norm"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_alias_global",
        "product_aliases",
        ["store", "raw_text_norm"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )

    op.create_table(
        "receipt_imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("store", sa.String(64), nullable=True),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("line_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_receipt_imports_user_id", "receipt_imports", ["user_id"])
    op.create_index(
        "ix_receipt_imports_user_created", "receipt_imports", ["user_id", "created_at"]
    )

    op.execute(
        "ALTER TABLE inventory_logs ADD COLUMN IF NOT EXISTS receipt_import_id INTEGER "
        "REFERENCES receipt_imports(id) ON DELETE SET NULL"
    )
    op.create_index(
        "ix_inventory_logs_receipt_import", "inventory_logs", ["receipt_import_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_logs_receipt_import", table_name="inventory_logs")
    op.execute("ALTER TABLE inventory_logs DROP COLUMN IF EXISTS receipt_import_id")
    op.drop_table("receipt_imports")
    op.drop_table("product_aliases")
