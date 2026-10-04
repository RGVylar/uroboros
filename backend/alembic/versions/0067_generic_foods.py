"""Alimentos genéricos: catálogo propio sin marca, con nombre en es/en/pt

Revision ID: 0067
Revises: 0066
Create Date: 2026-10-04

Un tester pedía poder apuntar "pavo" sin buscar de qué marca es. Los genéricos
van en la misma tabla de productos (el diario, las recetas y la despensa ya
saben usarlos) con source='generic', una clave estable y las traducciones del
nombre. Los datos están en app/data/generic_foods.py.
"""

from alembic import op
import sqlalchemy as sa

from app.services.generic_foods import sync_generic_foods

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Un valor nuevo de un enum no se puede usar en la misma transacción en
    # que se crea: va aparte, en autocommit.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE product_source ADD VALUE IF NOT EXISTS 'generic'")

    op.add_column("products", sa.Column("name_en", sa.String(255), nullable=True))
    op.add_column("products", sa.Column("name_pt", sa.String(255), nullable=True))
    op.add_column("products", sa.Column("generic_key", sa.String(64), nullable=True))
    op.create_index("ix_products_generic_key", "products", ["generic_key"], unique=True)

    sync_generic_foods(op.get_bind())


def downgrade() -> None:
    # Las filas se quedan como productos manuales: el diario, las recetas o la
    # despensa de alguien pueden apuntar a ellas. El valor del enum también se
    # queda (Postgres no deja quitarlo).
    op.execute("UPDATE products SET source = 'manual' WHERE source = 'generic'")
    op.drop_index("ix_products_generic_key", table_name="products")
    op.drop_column("products", "generic_key")
    op.drop_column("products", "name_pt")
    op.drop_column("products", "name_en")
