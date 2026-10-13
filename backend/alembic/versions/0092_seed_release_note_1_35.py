"""Seed the release note for 1.35 (compartir recetas fuera de la app)

Revision ID: 0092
Revises: 0091
Create Date: 2026-10-13

Data migration, misma forma que 0090. Va como `minor`: enlace público de las
recetas con su página, imagen para historias y App Links en Android.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0092"
down_revision = "0091"
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
            "version": "1.35",
            "title": {
                "es": "Tus recetas, fuera de la app",
                "en": "Your recipes, outside the app",
                "pt": "As tuas receitas, fora da app",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Comparte una receta con un enlace",
                        "en": "Share a recipe with a link",
                        "pt": "Partilha uma receita com uma ligação",
                    },
                    "desc": {
                        "es": "Al compartir una receta tuya va con un enlace: quien lo abre la ve con sus macros, puede cambiar las raciones y guardarla en su Uroboros en un toque. Si cambias de idea, retira el enlace desde la receta.",
                        "en": "When you share one of your recipes it comes with a link: whoever opens it sees the macros, can change the servings and save it to their Uroboros in one tap. Changed your mind? Remove the link from the recipe.",
                        "pt": "Ao partilhar uma receita tua vai com uma ligação: quem a abre vê os macros, pode mudar as doses e guardá-la no seu Uroboros num toque. Se mudares de ideias, retira a ligação a partir da receita.",
                    },
                },
                {
                    "type": "nuevo",
                    "title": {
                        "es": "La receta como imagen",
                        "en": "The recipe as an image",
                        "pt": "A receita como imagem",
                    },
                    "desc": {
                        "es": "Desde la receta, «Compartir como imagen» crea una tarjeta vertical para tus historias, con las kcal por ración y un QR para guardarla.",
                        "en": "From the recipe, “Share as image” creates a vertical card for your stories, with the kcal per serving and a QR code to save it.",
                        "pt": "A partir da receita, «Partilhar como imagem» cria um cartão vertical para as tuas histórias, com as kcal por dose e um QR para a guardar.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Los enlaces de recetas abren la app",
                        "en": "Recipe links open the app",
                        "pt": "As ligações de receitas abrem a app",
                    },
                    "desc": {
                        "es": "En Android, al tocar el enlace o escanear el QR de una receta con la app instalada, se abre directamente en Uroboros.",
                        "en": "On Android, tapping a recipe link or scanning its QR code with the app installed opens it straight in Uroboros.",
                        "pt": "No Android, ao tocar na ligação ou ler o QR de uma receita com a app instalada, abre-se diretamente no Uroboros.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.35'")
