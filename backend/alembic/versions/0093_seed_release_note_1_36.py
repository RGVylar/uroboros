"""Seed the release note for 1.36 (imagen de receta entera en WhatsApp)

Revision ID: 0093
Revises: 0092
Create Date: 2026-10-13

Data migration, misma forma que 0092. Va como `minor`: la imagen de la receta
en 4:5 y el arreglo de los minutos con decimales.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0093"
down_revision = "0092"
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
            "version": "1.36",
            "title": {
                "es": "La receta, entera en el chat",
                "en": "The whole recipe in the chat",
                "pt": "A receita inteira no chat",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "La imagen de la receta se ve entera",
                        "en": "The recipe image shows in full",
                        "pt": "A imagem da receita vê-se inteira",
                    },
                    "desc": {
                        "es": "«Compartir como imagen» crea ahora una tarjeta que WhatsApp e Instagram muestran completa, con todos los ingredientes.",
                        "en": "“Share as image” now makes a card that WhatsApp and Instagram show in full, with every ingredient.",
                        "pt": "«Partilhar como imagem» cria agora um cartão que o WhatsApp e o Instagram mostram completo, com todos os ingredientes.",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "Minutos con decimales",
                        "en": "Minutes with decimals",
                        "pt": "Minutos com decimais",
                    },
                    "desc": {
                        "es": "Poner, por ejemplo, 0,5 minutos de cocción en una receta ya no da un error al guardar.",
                        "en": "Entering, say, 0.5 minutes of cooking in a recipe no longer fails when saving.",
                        "pt": "Pôr, por exemplo, 0,5 minutos de cozedura numa receita já não dá erro ao guardar.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.36'")
