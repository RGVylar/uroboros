"""Add recipe cooking card: steps, servings, prep/cook minutes

Revision ID: 0062
Revises: 0061
Create Date: 2026-10-03

Hasta ahora una receta era solo una lista de ingredientes para registrar
macros. Ahora también dice cómo se hace: pasos numerados, raciones y tiempos
de preparación y cocción, que viajan al compartirla por texto. Todo opcional;
las recetas existentes quedan con cero pasos y sin tiempos.
"""
from alembic import op

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE recipes ADD COLUMN IF NOT EXISTS steps JSON NOT NULL DEFAULT '[]'")
    op.execute("ALTER TABLE recipes ADD COLUMN IF NOT EXISTS servings INTEGER")
    op.execute("ALTER TABLE recipes ADD COLUMN IF NOT EXISTS prep_minutes INTEGER")
    op.execute("ALTER TABLE recipes ADD COLUMN IF NOT EXISTS cook_minutes INTEGER")


def downgrade() -> None:
    for col in ("cook_minutes", "prep_minutes", "servings", "steps"):
        op.execute(f"ALTER TABLE recipes DROP COLUMN IF EXISTS {col}")
