"""Seed the release note for 1.29 (módulos del diario con color y el agua que se llena)

Revision ID: 0081
Revises: 0080
Create Date: 2026-10-08

Data migration, misma forma que 0079. Va como `minor`: cambia cómo se ven
los módulos del diario y la creatina pasa a la lista de suplementos.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0081"
down_revision = "0080"
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
            "version": "1.29",
            "title": {
                "es": "Un diario con más color",
                "en": "A more colourful diary",
                "pt": "Um diário com mais cor",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "Módulos nuevos en el diario",
                        "en": "New diary modules",
                        "pt": "Novos módulos no diário",
                    },
                    "desc": {
                        "es": "Agua, pasos, suplementos, estado del día y cheat day van en tarjetas de su color, con el dato en grande y el botón a mano. Y el agua se va llenando a medida que bebes.",
                        "en": "Water, steps, supplements, how you feel and cheat day now sit in cards of their own colour, with the number up front and the button within reach. And the water fills up as you drink.",
                        "pt": "Água, passos, suplementos, estado do dia e cheat day ficam em cartões da sua cor, com o número em grande e o botão à mão. E a água vai enchendo à medida que bebes.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "La creatina, en tus suplementos",
                        "en": "Creatine, in your supplements",
                        "pt": "A creatina, nos teus suplementos",
                    },
                    "desc": {
                        "es": "Ya no es un módulo aparte: si la usabas, la tienes en la lista de suplementos con los días que habías marcado.",
                        "en": "It's no longer a separate module: if you used it, it's now in your supplements list with the days you had ticked.",
                        "pt": "Já não é um módulo à parte: se a usavas, está na lista de suplementos com os dias que tinhas marcado.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.29'")
