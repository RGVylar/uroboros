"""Seed the release note for 1.25 (módulos y explicaciones a tiempo)

Revision ID: 0076
Revises: 0075
Create Date: 2026-10-06

Data migration, misma forma que 0074. Va como `major`: los interruptores de
ánimo, despensa y cheat days se han mudado de Ajustes a Módulos, y quien los
busque donde estaban tiene que enterarse aunque haya silenciado las novedades.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0076"
down_revision = "0075"
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
            "version": "1.25",
            "title": {
                "es": "Tu app, a tu medida",
                "en": "Your app, your way",
                "pt": "A tua app, à tua medida",
            },
            "importance": "major",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Elige qué ves",
                        "en": "Choose what you see",
                        "pt": "Escolhe o que vês",
                    },
                    "desc": {
                        "es": "En Ajustes → Módulos enciendes solo lo que usas: agua, peso, medidas, suplementos, ánimo, despensa, cheat days… Lo que apagas desaparece del diario y del menú, y tus datos se quedan.",
                        "en": "In Settings → Modules, turn on only what you use: water, weight, measurements, supplements, mood, pantry, cheat days… Anything you turn off disappears from the diary and menu, and your data stays.",
                        "pt": "Em Definições → Módulos ligas só o que usas: água, peso, medidas, suplementos, humor, despensa, cheat days… O que desligas desaparece do diário e do menu, e os teus dados ficam guardados.",
                    },
                },
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Explicaciones cuando hacen falta",
                        "en": "Explanations when you need them",
                        "pt": "Explicações quando fazem falta",
                    },
                    "desc": {
                        "es": "La primera vez que te cruzas con el duelo, la adherencia, pareja o amigo y otras cosas que no se adivinan, te las contamos en dos líneas. Con el botón ⓘ las vuelves a leer.",
                        "en": "The first time you come across the duel, adherence, partner vs. friend and other things that aren’t obvious, we explain them in two lines. Tap ⓘ to read them again.",
                        "pt": "Da primeira vez que te cruzas com o duelo, a adesão, par ou amigo e outras coisas que não se adivinham, explicamos em duas linhas. Com o botão ⓘ voltas a lê-las.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.25'")
