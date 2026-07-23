"""Seed the release note for 1.9 (la app en inglés y portugués)

Revision ID: 0044
Revises: 0043
Create Date: 2026-07-23

Data migration, misma forma que 0037/0038/0043. Marcada `major`: cambia el
idioma de toda la interfaz, así que conviene que la vea también quien tenga el
opt-out de novedades menores.

Ojo: las notas de versión solo existen en español (ver la decisión en
documentation/CHANGELOG.md). Traducirlas obligaría a escribir cada nota tres
veces en cada release, y se descartó por coste recurrente.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0044"
down_revision = "0043"
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
            "version": "1.9",
            "title": "uroboros habla inglés y portugués",
            "importance": "major",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": "Elige tu idioma",
                    "desc": "Español, inglés y portugués. Lo encuentras en Ajustes → Idioma. La primera vez la app coge el idioma de tu móvil sola; si eliges uno a mano, se queda fijo.",
                },
                {
                    "type": "nuevo",
                    "title": "Fechas y números en tu idioma",
                    "desc": "El calendario, los días de la semana y los meses ya no están en español a la fuerza: se adaptan al idioma que tengas puesto.",
                },
                {
                    "type": "mejora",
                    "title": "La página de invitación, traducida",
                    "desc": "El enlace que compartes con quien quieras invitar detecta el idioma de su navegador y se muestra en inglés o portugués si toca.",
                },
                {
                    "type": "mejora",
                    "title": "Widgets de Android traducidos",
                    "desc": "Los accesos rápidos de la pantalla de inicio siguen el idioma del sistema.",
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM release_notes WHERE version = '1.9'"))
