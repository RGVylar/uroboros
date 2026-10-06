"""Seed the release note for 1.27 (explicaciones con ejemplo y arreglos del repaso)

Revision ID: 0078
Revises: 0077
Create Date: 2026-10-06

Data migration, misma forma que 0077. Va como `minor`: explicaciones más
claras y arreglos, nada que se haya movido de sitio.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0078"
down_revision = "0077"
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
            "version": "1.27",
            "title": {
                "es": "Explicaciones que se ven",
                "en": "Explanations you can see",
                "pt": "Explicações que se veem",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "Cada explicación, con su ejemplo",
                        "en": "Every explanation, with an example",
                        "pt": "Cada explicação, com o seu exemplo",
                    },
                    "desc": {
                        "es": "Las explicaciones (y el botón ⓘ) enseñan cómo es aquello de lo que hablan: la tarjeta de tu pareja, el marcador del duelo, una semana de adherencia…",
                        "en": "Explanations (and the ⓘ button) now show what they talk about: your partner's card, the duel scoreboard, a week of adherence…",
                        "pt": "As explicações (e o botão ⓘ) mostram aquilo de que falam: o cartão do teu par, o marcador do duelo, uma semana de adesão…",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "La introducción no toca tus objetivos",
                        "en": "The intro leaves your goals alone",
                        "pt": "A introdução não mexe nos teus objetivos",
                    },
                    "desc": {
                        "es": "Repasarla desde Ajustes ya no cambia tus calorías y macros. Y el peso que pones al empezar queda como tu primer registro.",
                        "en": "Going through it again from Settings no longer changes your calories and macros. And the weight you enter at the start becomes your first entry.",
                        "pt": "Revê-la nas Definições já não muda as tuas calorias e macros. E o peso que indicas ao começar fica como o teu primeiro registo.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Pareja y recetas, más claras",
                        "en": "Partner and recipes, clearer",
                        "pt": "Par e receitas, mais claros",
                    },
                    "desc": {
                        "es": "Las solicitudes pendientes se ven al entrar, el aviso desaparece al aceptarlas y los ingredientes de una receta se buscan mientras escribes.",
                        "en": "Pending requests show up straight away, the badge clears when you accept them, and recipe ingredients are searched as you type.",
                        "pt": "Os pedidos pendentes veem-se logo ao entrar, o aviso desaparece ao aceitá-los e os ingredientes de uma receita procuram-se enquanto escreves.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.27'")
