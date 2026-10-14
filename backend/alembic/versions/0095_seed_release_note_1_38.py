"""Seed the release note for 1.38 (recetas para dos, despensa más clara)

Revision ID: 0095
Revises: 0094
Create Date: 2026-10-14

Data migration, misma forma que 0094. Va como `major`: cambia cómo se apunta
una receta para los dos (antes contaba el doble) y la despensa se renombra.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0095"
down_revision = "0094"
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
            "version": "1.38",
            "title": {
                "es": "Recetas para dos y una despensa más clara",
                "en": "Recipes for two and a clearer pantry",
                "pt": "Receitas para dois e uma despensa mais clara",
            },
            "importance": "major",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "Una receta para los dos se reparte",
                        "en": "A recipe for two is split",
                        "pt": "Uma receita para os dois é repartida",
                    },
                    "desc": {
                        "es": "Al apuntar una receta para los dos se reparte a medias y cada uno puede ajustar sus gramos. Antes se apuntaba entera a cada uno.",
                        "en": "Logging a recipe for both of you now splits it in half, and each of you can adjust your grams. Before, each of you got the whole thing.",
                        "pt": "Ao registar uma receita para os dois, é repartida a meias e cada um pode ajustar os seus gramas. Antes ficava inteira para cada um.",
                    },
                },
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Tus recetas, con su nombre en el diario",
                        "en": "Your recipes, by name in the diary",
                        "pt": "As tuas receitas, com nome no diário",
                    },
                    "desc": {
                        "es": "Lo que registras como receta aparece agrupado bajo su nombre, y puedes borrar solo un ingrediente o la receta entera.",
                        "en": "Whatever you log as a recipe is grouped under its name, and you can delete one ingredient or the whole recipe.",
                        "pt": "O que registas como receita aparece agrupado com o seu nome, e podes apagar só um ingrediente ou a receita inteira.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Despensa más fácil",
                        "en": "An easier pantry",
                        "pt": "Despensa mais fácil",
                    },
                    "desc": {
                        "es": "Ahora se llama Despensa en toda la app, busca mientras escribes y se puede activar desde la bienvenida.",
                        "en": "It's now called Pantry everywhere, searches as you type and can be turned on from the welcome screens.",
                        "pt": "Agora chama-se Despensa em toda a app, pesquisa enquanto escreves e pode ser ativada nas boas-vindas.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Más ayuda para empezar",
                        "en": "More help to get started",
                        "pt": "Mais ajuda para começar",
                    },
                    "desc": {
                        "es": "Nueva explicación de cómo funciona la olla, y avisos claros de qué falta para apuntar comida por tu pareja.",
                        "en": "A new explanation of how pots work, and clear hints on what's missing to log food for your partner.",
                        "pt": "Nova explicação de como funciona a panela, e avisos claros do que falta para registar comida pelo teu par.",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "Arreglos",
                        "en": "Fixes",
                        "pt": "Correções",
                    },
                    "desc": {
                        "es": "Los gramos de tu pareja se actualizan al editarlos, el diario carga más rápido y la constancia no te cuenta días anteriores a tu cuenta.",
                        "en": "Your partner's grams update right after editing them, the diary loads faster and consistency no longer counts days before your account existed.",
                        "pt": "Os gramas do teu par atualizam-se ao editá-los, o diário carrega mais depressa e a constância não conta dias anteriores à tua conta.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.38'")
