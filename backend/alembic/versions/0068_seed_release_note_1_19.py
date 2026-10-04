"""Seed the release note for 1.19 (alimentos genéricos)

Revision ID: 0068
Revises: 0067
Create Date: 2026-10-04

Data migration, misma forma que 0066. Cambia lo primero que ves al buscar un
alimento, pero no reglas ni datos de nadie: va como `minor`.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0068"
down_revision = "0067"
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
            "version": "1.19",
            "title": {
                "es": "Alimentos sin marca",
                "en": "Unbranded foods",
                "pt": "Alimentos sem marca",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Alimentos genéricos",
                        "en": "Generic foods",
                        "pt": "Alimentos genéricos",
                    },
                    "desc": {
                        "es": "Busca «pavo» o «arroz» y lo primero que sale es la versión genérica, con valores medios, sin tener que elegir marca. Lo que cambia al cocinarlo viene en crudo y cocinado.",
                        "en": "Search for “turkey” or “rice” and the generic version comes first, with average values, no brand to pick. Foods that change when cooked come both raw and cooked.",
                        "pt": "Pesquisa «peru» ou «arroz» e a versão genérica aparece primeiro, com valores médios, sem teres de escolher marca. O que muda ao cozinhar vem cru e cozinhado.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.19'")
