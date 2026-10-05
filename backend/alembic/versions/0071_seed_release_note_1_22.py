"""Seed the release note for 1.22 (los pasos piden permiso de verdad)

Revision ID: 0071
Revises: 0070
Create Date: 2026-10-05

Data migration, misma forma que 0070. Un arreglo solo de Android: va como `minor`.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0071"
down_revision = "0070"
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
            "version": "1.22",
            "title": {
                "es": "Pasos de Health Connect",
                "en": "Health Connect steps",
                "pt": "Passos do Health Connect",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "fix",
                    "title": {
                        "es": "Ya se pueden conectar los pasos",
                        "en": "Steps can now be connected",
                        "pt": "Já é possível ligar os passos",
                    },
                    "desc": {
                        "es": "Al activar los pasos en Ajustes no pasaba nada: ni pedía permiso ni avisaba. Ahora se abre Health Connect para darlo y tus pasos aparecen en el diario.",
                        "en": "Turning on steps in Settings did nothing: no permission prompt, no message. Now Health Connect opens so you can allow it, and your steps show up in your diary.",
                        "pt": "Ao ativar os passos nas Definições não acontecia nada: nem pedia permissão nem avisava. Agora abre o Health Connect para a dares e os teus passos aparecem no diário.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.22'")
