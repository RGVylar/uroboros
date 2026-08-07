"""Add users.feature_flags

Revision ID: 0051
Revises: 0050
Create Date: 2026-08-07

Lista de features sin terminar que este usuario puede ver. Null o [] = ninguna,
que es lo que tiene todo el mundo, así que las filas existentes no necesitan
backfill.

Es un **permiso, no un rol**: "puede ver cosas sin terminar". Deliberadamente no
es un `is_admin`, porque quien prueba una feature a medias no tiene por qué ser
administrador de nada — la pareja del autor, un par de amigos. Un rol obligaría
a darles poderes que no necesitan.

Se activa a mano, que para esto sobra con SQL:

    UPDATE users SET feature_flags = '["receipt_scan"]' WHERE email = '...';

Y se quita con `feature_flags = NULL`. Cuando la feature sale del flag, se borra
el gating del código; las filas se quedan con un flag que ya no mira nadie y no
molestan.
"""
from alembic import op

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS feature_flags JSON")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS feature_flags")
