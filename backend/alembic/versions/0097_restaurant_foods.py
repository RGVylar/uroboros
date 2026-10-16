"""Carta de cadenas de comida rápida: McDonald's, Burger King, Domino's, Telepizza y Taco Bell

Revision ID: 0097
Revises: 0096
Create Date: 2026-10-16

Un tester pedía poder apuntar "la pizza barbacoa del Domino's" sin buscar sus
macros. Van en la tabla de productos como los genéricos, con
source='restaurant', la cadena como marca, una clave estable y la ración que
publica la cadena. Los datos están en app/data/restaurant_foods.py.
"""

from alembic import op
import sqlalchemy as sa

from app.services.restaurant_foods import sync_restaurant_foods

revision = "0097"
down_revision = "0096"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Un valor nuevo de un enum no se puede usar en la misma transacción en
    # que se crea: va aparte, en autocommit.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE product_source ADD VALUE IF NOT EXISTS 'restaurant'")

    op.add_column("products", sa.Column("restaurant_key", sa.String(64), nullable=True))
    op.create_index("ix_products_restaurant_key", "products", ["restaurant_key"], unique=True)

    sync_restaurant_foods(op.get_bind())


def downgrade() -> None:
    # Las filas se quedan como productos manuales: el diario de alguien puede
    # apuntar a ellas. El valor del enum también se queda.
    op.execute("UPDATE products SET source = 'manual' WHERE source = 'restaurant'")
    op.drop_index("ix_products_restaurant_key", table_name="products")
    op.drop_column("products", "restaurant_key")
