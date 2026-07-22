"""Seed the release note for 1.8 (ver el día de tu pareja en tu diario)

Revision ID: 0043
Revises: 0042
Create Date: 2026-07-22

Data migration, same shape as 0037/0038. Marked `major`: es una función nueva
visible, así que se muestra también a quien tenga el opt-out de novedades menores.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None

_release_notes = sa.table(
    "release_notes",
    sa.column("version", sa.String),
    sa.column("title", sa.String),
    sa.column("items", sa.JSON),
    sa.column("importance", sa.String),
    sa.column("published", sa.Boolean),
    sa.column("published_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    op.bulk_insert(_release_notes, [
        {
            "version": "1.8",
            "title": "El día de tu pareja, en tu diario",
            "importance": "major",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": "Ver lo que lleva tu pareja hoy",
                    "desc": "Un chip arriba de tu diario resume su día (kcal y proteína). Tócalo y sus comidas aparecen intercaladas entre las tuyas, en su color, para que os coordinéis.",
                },
                {
                    "type": "nuevo",
                    "title": "Ponértelo a ti también",
                    "desc": "¿Ha comido algo que tú también quieres registrar? Con el botón + de cada plato suyo te lo copias a tu diario al instante.",
                },
                {
                    "type": "nuevo",
                    "title": "Tu color de identidad",
                    "desc": "Elige tu color en el perfil: es el aro de tu avatar y el tono con el que te ve tu pareja. Sus calorías nunca se suman a tus totales.",
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM release_notes WHERE version = '1.8'"))
