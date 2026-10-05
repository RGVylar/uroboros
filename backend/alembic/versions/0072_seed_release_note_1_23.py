"""Seed the release note for 1.23 (todo abierto durante el lanzamiento)

Revision ID: 0072
Revises: 0071
Create Date: 2026-10-05

Data migration, misma forma que 0071. Va como `major`: cambia lo que puede
hacer cualquier usuario nuevo, y quien tenga las notas silenciadas también
debería enterarse. Sin precios ni "gratis" (ver la regla de marketing).
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0072"
down_revision = "0071"
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
            "version": "1.23",
            "title": {
                "es": "Todo abierto durante el lanzamiento",
                "en": "Everything unlocked during launch",
                "pt": "Tudo desbloqueado durante o lançamento",
            },
            "importance": "major",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Acceso de lanzamiento",
                        "en": "Launch access",
                        "pt": "Acesso de lançamento",
                    },
                    "desc": {
                        "es": "Mientras dure el lanzamiento tienes todas las funciones: despensa, lista de la compra, ejercicio, medidas, historial completo y recetas sin límite. Lo verás en Ajustes → Plan. Cuando llegue Premium, te avisaremos con tiempo.",
                        "en": "For as long as the launch lasts you get every feature: pantry, shopping list, exercise, body measurements, full history and unlimited recipes. You'll see it under Settings → Plan. When Premium arrives, we'll let you know well in advance.",
                        "pt": "Enquanto durar o lançamento tens todas as funcionalidades: despensa, lista de compras, exercício, medidas, histórico completo e receitas sem limite. Vais vê-lo em Definições → Plano. Quando o Premium chegar, avisamos-te com antecedência.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.23'")
