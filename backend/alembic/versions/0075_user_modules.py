"""Add users.modules and users.seen_tips

Revision ID: 0075
Revises: 0074
Create Date: 2026-10-06

`modules`: qué partes de la app quiere ver cada usuario (agua, peso, ánimo…),
como objeto `{"mood": true, "water": false}`. Solo guarda lo que el usuario ha
tocado; lo que falta toma el valor por defecto de `services/modules.py`. Null =
nada tocado, así que las filas existentes no necesitan backfill.

`seen_tips`: ids de las explicaciones que ya ha cerrado. En el servidor y no en
localStorage para que no se repitan en cada dispositivo (y porque iOS puede
vaciar el almacenamiento de una PWA).
"""
from alembic import op

revision = "0075"
down_revision = "0074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS modules JSON")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS seen_tips JSON")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS seen_tips")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS modules")
