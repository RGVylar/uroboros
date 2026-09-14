"""Add recipes.total_weight

Revision ID: 0056
Revises: 0055
Create Date: 2026-09-14

Una receta siempre se registraba entera. Ahora se puede registrar una ración
en gramos ("120 g del pollo con arroz") y para eso hace falta saber cuánto
pesa la receta: por defecto la suma de ingredientes en crudo, pero un guiso
pierde agua, así que quien quiera puede decir el peso final del plato hecho.
Nulo = suma de ingredientes, con lo que las recetas existentes no cambian.
"""
from alembic import op

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE recipes ADD COLUMN IF NOT EXISTS total_weight FLOAT")


def downgrade() -> None:
    op.execute("ALTER TABLE recipes DROP COLUMN IF EXISTS total_weight")
