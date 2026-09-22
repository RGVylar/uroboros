"""Seed the release note for 1.15 (ajustar ingredientes al registrar una receta)

Revision ID: 0059
Revises: 0058
Create Date: 2026-09-22

Data migration, misma forma que 0058. Una sola novedad visible y sin cambiar
nada que ya existiera, así que va como `minor`.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0059"
down_revision = "0058"
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
            "version": "1.15",
            "title": {
                "es": "Hoy, menos huevo y más pan",
                "en": "Today, less egg and more bread",
                "pt": "Hoje, menos ovo e mais pão",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Ajusta los ingredientes al registrar una receta",
                        "en": "Adjust the ingredients when logging a recipe",
                        "pt": "Ajusta os ingredientes ao registar uma receita",
                    },
                    "desc": {
                        "es": "Al añadir una receta al diario, además de «toda» o «una ración en gramos», ahora puedes tocar «Ajustar ingredientes» y cambiar lo que tomas hoy de cada uno: menos huevo, más pan, o 0 para saltarlo. Las calorías se recalculan al momento y la receta guardada no cambia.",
                        "en": "When adding a recipe to your diary, besides “whole” or “a portion in grams”, you can now tap “Adjust ingredients” and change how much of each one you're having today: less egg, more bread, or 0 to skip it. Calories update on the spot and the saved recipe stays as it is.",
                        "pt": "Ao adicionar uma receita ao diário, além de «inteira» ou «uma dose em gramas», agora podes tocar em «Ajustar ingredientes» e mudar o que tomas hoje de cada um: menos ovo, mais pão, ou 0 para o saltar. As calorias recalculam-se na hora e a receita guardada não muda.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.15'")
