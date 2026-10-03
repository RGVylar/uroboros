"""Seed the release note for 1.17 (recetas con pasos, pasos de Health Connect)

Revision ID: 0064
Revises: 0063
Create Date: 2026-10-03

Data migration, misma forma que 0061. Dos novedades que no cambian reglas
sociales ni datos que otros ven, así que va como `minor`.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0064"
down_revision = "0063"
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
            "version": "1.17",
            "title": {
                "es": "Recetas paso a paso",
                "en": "Step-by-step recipes",
                "pt": "Receitas passo a passo",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Recetas con pasos",
                        "en": "Recipes with steps",
                        "pt": "Receitas com passos",
                    },
                    "desc": {
                        "es": "Guarda cómo se hace cada receta, con pasos numerados, raciones y tiempos de preparación y cocción. Ábrela con 📖 para verla entera y compártela con todo: ingredientes, pasos y macros.",
                        "en": "Save how each recipe is made, with numbered steps, servings, and prep and cooking times. Open it with 📖 to see it all and share the whole thing: ingredients, steps and macros.",
                        "pt": "Guarda como se faz cada receita, com passos numerados, porções e tempos de preparação e cozedura. Abre-a com 📖 para a ver inteira e partilha-a com tudo: ingredientes, passos e macros.",
                    },
                },
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Pasos del móvil",
                        "en": "Steps from your phone",
                        "pt": "Passos do telemóvel",
                    },
                    "desc": {
                        "es": "En Android, conecta Health Connect desde Ajustes > Salud y verás tus pasos del día en el diario.",
                        "en": "On Android, connect Health Connect from Settings > Health and you'll see today's steps in your diary.",
                        "pt": "No Android, liga o Health Connect em Definições > Saúde e vais ver os passos do dia no diário.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.17'")
