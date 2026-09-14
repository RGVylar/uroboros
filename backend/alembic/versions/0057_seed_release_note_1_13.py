"""Seed the release note for 1.13 (raciones de receta en gramos)

Revision ID: 0057
Revises: 0056
Create Date: 2026-09-14

Data migration, misma forma que 0055. Una sola novedad, pero cambia cómo se
registra una receta (antes siempre entera) y por eso merece nota y versión
propias en vez de colarse en la 1.12, que ya está sembrada.

Marcada `minor`: nada que cambie reglas sociales ni datos que otros ven.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0057"
down_revision = "0056"
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
            "version": "1.13",
            "title": {
                "es": "Recetas por gramos",
                "en": "Recipes by the gram",
                "pt": "Receitas ao grama",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Registra una ración de receta, no la receta entera",
                        "en": "Log a portion of a recipe, not the whole thing",
                        "pt": "Regista uma dose da receita, não a receita inteira",
                    },
                    "desc": {
                        "es": "Al registrar una receta eliges «toda» o escribes los gramos que te has servido: 120 g de un guiso de 400 g apunta el 30 % de cada ingrediente. Ves las kcal y macros de esa ración antes de confirmar.",
                        "en": "When logging a recipe you pick “whole” or type the grams you served yourself: 120 g of a 400 g stew logs 30% of each ingredient. You see the kcal and macros of that portion before confirming.",
                        "pt": "Ao registar uma receita escolhes «inteira» ou escreves os gramas que te serviste: 120 g de um guisado de 400 g regista 30% de cada ingrediente. Vês as kcal e macros dessa dose antes de confirmar.",
                    },
                },
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Peso final del plato y macros por 100 g",
                        "en": "Cooked weight and macros per 100 g",
                        "pt": "Peso final do prato e macros por 100 g",
                    },
                    "desc": {
                        "es": "Al crear o editar una receta puedes indicar cuánto pesa ya cocinada (un guiso pierde agua). Con eso, la receta muestra sus kcal por 100 g y las raciones salen exactas. Si lo dejas vacío, se usa la suma de ingredientes.",
                        "en": "When creating or editing a recipe you can say what it weighs once cooked (a stew loses water). With that, the recipe shows its kcal per 100 g and portions come out exact. Leave it empty to use the sum of ingredients.",
                        "pt": "Ao criar ou editar uma receita podes indicar quanto pesa já cozinhada (um guisado perde água). Com isso, a receita mostra as kcal por 100 g e as doses saem exatas. Se deixares vazio, usa-se a soma dos ingredientes.",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "Registrar solo para tu pareja desde una receta",
                        "en": "Logging only for your partner from a recipe",
                        "pt": "Registar só para o teu par a partir de uma receita",
                    },
                    "desc": {
                        "es": "La opción «solo para» acababa en tu propio diario. Y las recetas registradas desde la pantalla de Recetas ya cuentan como frecuentes.",
                        "en": "The “only for” option ended up in your own diary. And recipes logged from the Recipes screen now count as frequent.",
                        "pt": "A opção «só para» acabava no teu próprio diário. E as receitas registadas a partir do ecrã de Receitas já contam como frequentes.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.13'")
