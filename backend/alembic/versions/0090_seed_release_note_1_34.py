"""Seed the release note for 1.34 (ingredientes en los pasos)

Revision ID: 0090
Revises: 0089
Create Date: 2026-10-13

Data migration, misma forma que 0089. Va como `minor`: ingredientes nombrados
en los pasos, el registro de recetas desde Añadir completo y la tapa de la olla.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0090"
down_revision = "0089"
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
            "version": "1.34",
            "title": {
                "es": "Cada ingrediente en su paso",
                "en": "Every ingredient in its step",
                "pt": "Cada ingrediente no seu passo",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Nombra ingredientes en los pasos",
                        "en": "Mention ingredients in the steps",
                        "pt": "Refere ingredientes nos passos",
                    },
                    "desc": {
                        "es": "Al escribir los pasos de una receta, pon @ y elige un ingrediente: se verá con su cantidad. Si en un paso solo va una parte, escribe @Aceite de oliva:10.",
                        "en": "When writing a recipe's steps, type @ and pick an ingredient: it shows with its amount. If a step only uses part of it, write @Olive oil:10.",
                        "pt": "Ao escrever os passos de uma receita, põe @ e escolhe um ingrediente: aparece com a quantidade. Se num passo só vai uma parte, escreve @Azeite:10.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Recetas desde Añadir, completas",
                        "en": "Recipes from Add, complete",
                        "pt": "Receitas a partir de Adicionar, completas",
                    },
                    "desc": {
                        "es": "Al apuntar una receta desde Añadir ya puedes elegir la comida, el día y si es también para tu pareja, o convertirla en una olla.",
                        "en": "When logging a recipe from Add you can now pick the meal, the day and whether it's for your partner too, or turn it into a pot.",
                        "pt": "Ao registar uma receita a partir de Adicionar já podes escolher a refeição, o dia e se é também para o teu par, ou transformá-la numa panela.",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "La tapa, por delante",
                        "en": "The lid in front",
                        "pt": "A tampa à frente",
                    },
                    "desc": {
                        "es": "Con la olla llena, el caldo ya no se ve a través del borde.",
                        "en": "With a full pot, the stew no longer shows through the rim.",
                        "pt": "Com a panela cheia, o caldo já não se vê através da borda.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.34'")
