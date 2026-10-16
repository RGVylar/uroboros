"""Seed the release note for 1.40 (carta de cadenas de comida rápida)

Revision ID: 0098
Revises: 0097
Create Date: 2026-10-16

Data migration, misma forma que 0096. Va como `minor`: los productos de
McDonald's, Burger King, Domino's, Telepizza y Taco Bell salen en la búsqueda.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0098"
down_revision = "0097"
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
            "version": "1.40",
            "title": {
                "es": "La carta de las cadenas de comida rápida",
                "en": "Fast food chain menus",
                "pt": "Os menus das cadeias de fast food",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "McDonald's, Burger King, Domino's, Telepizza y Taco Bell",
                        "en": "McDonald's, Burger King, Domino's, Telepizza and Taco Bell",
                        "pt": "McDonald's, Burger King, Domino's, Telepizza e Taco Bell",
                    },
                    "desc": {
                        "es": "Busca \"pizza barbacoa dominos\" o \"big mac\" y apúntalo con los valores oficiales de cada cadena. Las hamburguesas y los tacos vienen con su ración ya puesta.",
                        "en": "Search \"pizza barbacoa dominos\" or \"big mac\" and log it with each chain's official values. Burgers and tacos come with their serving already set.",
                        "pt": "Pesquisa \"pizza barbacoa dominos\" ou \"big mac\" e regista-o com os valores oficiais de cada cadeia. Os hambúrgueres e os tacos já vêm com a dose definida.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.40'")
