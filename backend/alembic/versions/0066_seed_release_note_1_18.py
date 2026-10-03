"""Seed the release note for 1.18 (reportar un problema, botones de Amigos)

Revision ID: 0066
Revises: 0065
Create Date: 2026-10-03

Data migration, misma forma que 0064. Una herramienta nueva y un arreglo de
maquetación: nada que cambie reglas ni datos de otros, así que va como `minor`.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0066"
down_revision = "0065"
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
            "version": "1.18",
            "title": {
                "es": "Cuéntanos qué falla",
                "en": "Tell us what's broken",
                "pt": "Conta-nos o que falha",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Reportar un problema",
                        "en": "Report a problem",
                        "pt": "Reportar um problema",
                    },
                    "desc": {
                        "es": "Desde Ajustes puedes contarnos qué no funciona y adjuntar una captura. La versión de la app va incluida, así lo encontramos antes.",
                        "en": "From Settings you can tell us what isn't working and attach a screenshot. The app version is included, so we can track it down faster.",
                        "pt": "Em Definições podes contar-nos o que não funciona e anexar uma captura de ecrã. A versão da app vai incluída, para o encontrarmos mais depressa.",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "Amigos en pantallas estrechas",
                        "en": "Friends on narrow screens",
                        "pt": "Amigos em ecrãs estreitos",
                    },
                    "desc": {
                        "es": "Los botones de cada amigo ya no tapan su nombre.",
                        "en": "Each friend's buttons no longer cover their name.",
                        "pt": "Os botões de cada amigo já não tapam o nome.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.18'")
