"""Add users.avatar_photo

Revision ID: 0048
Revises: 0047
Create Date: 2026-07-29

Nombre del fichero WebP que el usuario ha subido como foto de perfil. Null =
sigue con el avatar predefinido o con el disco de la inicial, así que las filas
existentes no necesitan backfill.

Los ficheros viven fuera de la BD (MEDIA_DIR) y fuera del repo, porque el deploy
es un `git pull`. Ojo al restaurar un backup: la columna vuelve con el dump, los
ficheros no — hay que restaurar también el directorio.
"""
from alembic import op

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_photo VARCHAR(64)")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS avatar_photo")
