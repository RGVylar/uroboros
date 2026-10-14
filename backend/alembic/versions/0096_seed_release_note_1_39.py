"""Seed the release note for 1.39 (escanear ingredientes de receta)

Revision ID: 0096
Revises: 0095
Create Date: 2026-10-14

Data migration, misma forma que 0094. Va como `minor`: botón de escanear el
código de barras al crear o editar una receta.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0096"
down_revision = "0095"
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
            "version": "1.39",
            "title": {
                "es": "Escanea los ingredientes de tus recetas",
                "en": "Scan your recipe ingredients",
                "pt": "Digitaliza os ingredientes das receitas",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "Escanear al crear una receta",
                        "en": "Scan while creating a recipe",
                        "pt": "Digitalizar ao criar uma receita",
                    },
                    "desc": {
                        "es": "Al crear o editar una receta, el botón junto al código de barras abre la cámara y añade el ingrediente sin teclear el número.",
                        "en": "When creating or editing a recipe, the button next to the barcode opens the camera and adds the ingredient without typing the number.",
                        "pt": "Ao criar ou editar uma receita, o botão junto ao código de barras abre a câmara e adiciona o ingrediente sem escrever o número.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.39'")
