"""Add user_goals.cheat_days_per_week

Revision ID: 0053
Revises: 0052
Create Date: 2026-09-13

Hasta ahora el comodín no tenía tope: se podía activar los siete días de la
semana y la racha quedaba "protegida" sin registrar nada nunca. Ahora hay un
máximo semanal (lunes a domingo, la misma semana que usa el duelo), que el
usuario elige en Ajustes. Por defecto 1, que es lo que casi todo el mundo
entiende por "cheat day"; 7 equivale a sin límite.

Las filas existentes se quedan con 1: el cambio de comportamiento para quien
lo usaba a diario es deliberado, y siempre puede subirlo.
"""
from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE user_goals ADD COLUMN IF NOT EXISTS cheat_days_per_week INTEGER NOT NULL DEFAULT 1")


def downgrade() -> None:
    op.execute("ALTER TABLE user_goals DROP COLUMN IF EXISTS cheat_days_per_week")
