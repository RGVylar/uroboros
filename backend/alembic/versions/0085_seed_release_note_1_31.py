"""Seed the release note for 1.31 (revisión semanal de objetivos y tendencia del peso)

Revision ID: 0085
Revises: 0084
Create Date: 2026-10-08

Data migration, misma forma que 0083. Va como `minor`.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0085"
down_revision = "0084"
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
            "version": "1.31",
            "title": {
                "es": "Objetivos que se ajustan a ti",
                "en": "Goals that adjust to you",
                "pt": "Objetivos que se ajustam a ti",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Revisión semanal de tus calorías",
                        "en": "Weekly calorie check-in",
                        "pt": "Revisão semanal das tuas calorias",
                    },
                    "desc": {
                        "es": "Con lo que comes y lo que marca la báscula calculamos lo que gastas de verdad. Cada semana, si hace falta, te proponemos ajustar las calorías: lo aplicas con un toque.",
                        "en": "From what you eat and what the scale says we work out what you really burn. Each week, if needed, we suggest adjusting your calories: apply it with one tap.",
                        "pt": "Com o que comes e o que a balança marca calculamos o que gastas de verdade. Todas as semanas, se for preciso, propomos-te ajustar as calorias: aplicas com um toque.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "La tendencia de tu peso",
                        "en": "Your weight trend",
                        "pt": "A tendência do teu peso",
                    },
                    "desc": {
                        "es": "En Peso verás tu tendencia y cuánto cambia por semana, sin los altibajos de cada día.",
                        "en": "In Weight you'll see your trend and how much it changes per week, without the daily ups and downs.",
                        "pt": "Em Peso vais ver a tua tendência e quanto muda por semana, sem os altos e baixos de cada dia.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Elige qué seguir desde el principio",
                        "en": "Choose what to track from the start",
                        "pt": "Escolhe o que acompanhar desde o início",
                    },
                    "desc": {
                        "es": "La introducción pregunta qué quieres seguir (agua, peso, ejercicio…) y recuerda tus datos para la calculadora de objetivos.",
                        "en": "The introduction asks what you want to track (water, weight, exercise…) and remembers your details for the goals calculator.",
                        "pt": "A introdução pergunta o que queres acompanhar (água, peso, exercício…) e lembra os teus dados para a calculadora de objetivos.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.31'")
