"""Seed the release note for 1.28 (iconos propios en vez de emojis)

Revision ID: 0079
Revises: 0078
Create Date: 2026-10-06

Data migration, misma forma que 0078. Va como `minor`: cambia cómo se ve
casi todo, pero nada se ha movido de sitio.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0079"
down_revision = "0078"
branch_labels = None
depends_on = None

_release_notes = sa.table(
    "release_notes",
    sa.column("version", sa.String),
    sa.column("title", sa.JSON),
    sa.column("items", sa.JSON),
    sa.column("importance", sa.String),
    sa.column("published", sa.Boolean),
    sa.column("published_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    op.bulk_insert(_release_notes, [
        {
            "version": "1.28",
            "title": {
                "es": "Iconos nuevos",
                "en": "New icons",
                "pt": "Ícones novos",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "Adiós a los emojis",
                        "en": "Goodbye, emojis",
                        "pt": "Adeus aos emojis",
                    },
                    "desc": {
                        "es": "Botones, menús, avisos, el estado del día, las medallas y el duelo llevan ahora iconos propios de uroboros. Se ven igual en cualquier móvil y siguen los colores de la app.",
                        "en": "Buttons, menus, alerts, how you feel today, medals and the duel now use uroboros' own icons. They look the same on any phone and follow the app's colours.",
                        "pt": "Botões, menus, avisos, o estado do dia, as medalhas e o duelo usam agora ícones próprios do uroboros. Veem-se iguais em qualquer telemóvel e seguem as cores da app.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.28'")
