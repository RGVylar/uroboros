"""Add products.unit

Revision ID: 0054
Revises: 0053
Create Date: 2026-09-13

Hasta ahora la unidad de un producto la adivinaba el cliente por el nombre
("zumo" → ml) y no había forma de decir "esto va por unidades". Ahora el
producto lo lleva: 'g', 'ml' o 'unit'. Nulo = como hasta ahora, por nombre,
así las filas existentes no cambian de aspecto.

Para 'unit' los *_per_100g significan "por unidad" y una unidad son 100 g
internos, que es el factor por defecto que ya usa unit_conversions; así
diario, despensa y recetas siguen calculando exactamente igual.
"""
from alembic import op

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS unit VARCHAR(8)")


def downgrade() -> None:
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS unit")
