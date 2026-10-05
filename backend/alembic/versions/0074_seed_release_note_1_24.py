"""Seed the release note for 1.23 (tarjeta de pasos con la semana)

Revision ID: 0073
Revises: 0072
Create Date: 2026-10-05

Data migration, misma forma que 0071. Cambia cómo se ve el diario, no reglas ni datos
de nadie: va como `minor`.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0073"
down_revision = "0072"
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
                "es": "Tus pasos de la semana",
                "en": "Your steps this week",
                "pt": "Os teus passos da semana",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "Pasos junto al agua",
                        "en": "Steps next to water",
                        "pt": "Passos ao lado da água",
                    },
                    "desc": {
                        "es": "La tarjeta de pasos ahora va al lado del agua y enseña tus últimos 7 días en barras, con una línea para tu objetivo. El objetivo de pasos se cambia en Objetivos.",
                        "en": "The steps card now sits next to water and shows your last 7 days as bars, with a line for your goal. Change your steps goal in Goals.",
                        "pt": "O cartão de passos fica agora ao lado da água e mostra os teus últimos 7 dias em barras, com uma linha para o teu objetivo. O objetivo de passos muda-se em Objetivos.",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "Guardar objetivos ya no apaga nada",
                        "en": "Saving goals no longer turns things off",
                        "pt": "Guardar objetivos já não desativa nada",
                    },
                    "desc": {
                        "es": "Guardar la pantalla de Objetivos desactivaba los cheat days, el inventario y el ajuste de macros por ejercicio. Ya no.",
                        "en": "Saving the Goals screen used to turn off cheat days, the pantry and exercise macro adjustment. Not anymore.",
                        "pt": "Guardar o ecrã de Objetivos desativava os cheat days, o inventário e o ajuste de macros por exercício. Já não.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.23'")
