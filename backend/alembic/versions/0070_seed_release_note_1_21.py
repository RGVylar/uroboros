"""Seed the release note for 1.21 (activar los pasos en Android)

Revision ID: 0070
Revises: 0069
Create Date: 2026-10-05

Data migration, misma forma que 0069. Un arreglo solo de Android: va como `minor`.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0070"
down_revision = "0069"
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
            "version": "1.21",
            "title": {
                "es": "Pasos en Android",
                "en": "Steps on Android",
                "pt": "Passos no Android",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "fix",
                    "title": {
                        "es": "Activar los pasos",
                        "en": "Turning on steps",
                        "pt": "Ativar os passos",
                    },
                    "desc": {
                        "es": "En algunos móviles, al dar permiso en Health Connect los pasos se volvían a desactivar solos. Ahora se quedan activados y empiezan a leerse al momento.",
                        "en": "On some phones, steps turned themselves off again after granting access in Health Connect. Now they stay on and start syncing right away.",
                        "pt": "Em alguns telemóveis, depois de dar permissão no Health Connect os passos voltavam a desativar-se sozinhos. Agora ficam ativos e começam a ser lidos logo.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.21'")
