"""Enlace público de las recetas (/r/<código>)

Revision ID: 0091
Revises: 0090
Create Date: 2026-10-13

Código corto para compartir una receta fuera de la app: la página la sirve el
backend con tarjeta Open Graph y desde ella se guarda una copia. Nulo = la
receta no tiene enlace.
"""

from alembic import op
import sqlalchemy as sa

revision = "0091"
down_revision = "0090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("public_code", sa.String(16), nullable=True))
    op.create_index("ix_recipes_public_code", "recipes", ["public_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_recipes_public_code", table_name="recipes")
    op.drop_column("recipes", "public_code")
