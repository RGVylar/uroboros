"""Recalcula las kcal de productos de Open Food Facts guardados a 0 kcal

Revision ID: 0060
Revises: 0059
Create Date: 2026-09-26

El importador solo leía `energy-kcal_100g`; las fichas que traen la energía en
kJ, o las kcal a 0 con los macros rellenos, se guardaban a 0 kcal. Aquí se
rellenan con 4·P + 4·C + 9·G. Las que no tienen ni macros se quedan como están
(la búsqueda ya las oculta). Las entradas de diario no se tocan: copian los
valores al registrar y reescribir días pasados sería peor que dejarlos.
"""
from alembic import op

revision = "0060"
down_revision = "0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE products
        SET calories_per_100g = ROUND(CAST(4 * protein_per_100g + 4 * carbs_per_100g + 9 * fat_per_100g AS NUMERIC), 1)
        WHERE source = 'openfoodfacts'
          AND calories_per_100g <= 0
          AND (protein_per_100g + carbs_per_100g + fat_per_100g) > 0
        """
    )


def downgrade() -> None:
    # No se puede saber qué filas venían a 0: los valores corregidos se quedan.
    pass
