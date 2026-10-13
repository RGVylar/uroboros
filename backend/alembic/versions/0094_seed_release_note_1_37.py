"""Seed the release note for 1.37 (reiniciar explicaciones)

Revision ID: 0094
Revises: 0093
Create Date: 2026-10-13

Data migration, misma forma que 0093. Va como `minor`: un botón en Ajustes
para que las explicaciones vuelvan a salir.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0094"
down_revision = "0093"
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
            "version": "1.37",
            "title": {
                "es": "Vuelve a ver las explicaciones",
                "en": "See the tips again",
                "pt": "Volta a ver as explicações",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "Reiniciar explicaciones",
                        "en": "Reset tips",
                        "pt": "Repor explicações",
                    },
                    "desc": {
                        "es": "En Ajustes hay un botón para que las ayudas de cada pantalla vuelvan a salir, como la primera vez.",
                        "en": "Settings has a button to bring back the help on each screen, just like the first time.",
                        "pt": "Nas Definições há um botão para que as ajudas de cada ecrã voltem a aparecer, como da primeira vez.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.37'")
