"""Envase y ración de los productos de Open Food Facts

Revision ID: 0086
Revises: 0085
Create Date: 2026-10-13

OFF dice en qué se mide un producto (330 ml, 125 g), cuánto trae el envase y
cuánto es una ración. Antes no se pedía y las bebidas sin "zumo" o "leche" en
el nombre salían en gramos. `unit` ya existía; aquí van el envase y la ración.
Los productos ya guardados se rellenan solos la próxima vez que salen en una
búsqueda o se escanean.
"""

from alembic import op
import sqlalchemy as sa

revision = "0086"
down_revision = "0085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("package_qty", sa.Float(), nullable=True))
    op.add_column("products", sa.Column("serving_qty", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "serving_qty")
    op.drop_column("products", "package_qty")
