"""Seed the release note for 1.41 (gráfico de peso y deshacer al borrar)

Revision ID: 0100
Revises: 0099
Create Date: 2026-10-16

Data migration, misma forma que 0098. Va como `minor`: gráfico de peso con
puntos y tendencia, borrar deslizando y "Deshacer" en peso y diario.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0100"
down_revision = "0099"
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
            "version": "1.41",
            "title": {
                "es": "Un gráfico de peso más claro y deshacer al borrar",
                "en": "A clearer weight chart and undo on delete",
                "pt": "Um gráfico de peso mais claro e anular ao apagar",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "Gráfico de peso renovado",
                        "en": "Redesigned weight chart",
                        "pt": "Gráfico de peso renovado",
                    },
                    "desc": {
                        "es": "Cada pesaje es un punto y la línea es tu tendencia, con los kilos en el eje. Los días sin pesarte ya no se rellenan con una curva inventada.",
                        "en": "Each weigh-in is a dot and the line is your trend, with kilos on the axis. Days you didn't weigh yourself are no longer filled in with a made-up curve.",
                        "pt": "Cada pesagem é um ponto e a linha é a tua tendência, com os quilos no eixo. Os dias sem pesagem já não são preenchidos com uma curva inventada.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Registros de peso: diferencia y deslizar para borrar",
                        "en": "Weight entries: difference and swipe to delete",
                        "pt": "Registos de peso: diferença e deslizar para apagar",
                    },
                    "desc": {
                        "es": "Cada registro muestra cuánto ha cambiado desde el anterior. Para borrar uno, deslízalo a la izquierda.",
                        "en": "Each entry shows how much it changed since the previous one. To delete one, swipe it left.",
                        "pt": "Cada registo mostra quanto mudou desde o anterior. Para apagar um, desliza-o para a esquerda.",
                    },
                },
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Deshacer al borrar",
                        "en": "Undo on delete",
                        "pt": "Anular ao apagar",
                    },
                    "desc": {
                        "es": "Si borras un peso o una comida del diario sin querer, tienes unos segundos para recuperarlo con \"Deshacer\".",
                        "en": "If you delete a weight or a diary food by mistake, you have a few seconds to get it back with \"Undo\".",
                        "pt": "Se apagares um peso ou um alimento do diário sem querer, tens uns segundos para o recuperar com \"Anular\".",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.41'")
