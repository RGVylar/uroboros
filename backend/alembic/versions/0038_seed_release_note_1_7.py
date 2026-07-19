"""Seed the release note for 1.7 (pareja en editar y borrar)

Revision ID: 0038
Revises: 0037
Create Date: 2026-07-19

Data migration, same shape as 0033/0037. Marked `minor` — es un pulido de la
función de pareja, no un cambio de comportamiento gordo, así que respeta el
opt-out de novedades.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None

_release_notes = sa.table(
    "release_notes",
    sa.column("version", sa.String),
    sa.column("title", sa.String),
    sa.column("items", sa.JSON),
    sa.column("importance", sa.String),
    sa.column("published", sa.Boolean),
    sa.column("published_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    op.bulk_insert(_release_notes, [
        {
            "version": "1.7",
            "title": "Comida compartida, más fina",
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": "Cada uno con sus gramos",
                    "desc": "Al editar una comida que tu pareja también tiene, ajustáis la cantidad de cada uno por separado. Y si se le olvidó ponérsela, se la añades ahí mismo.",
                },
                {
                    "type": "mejora",
                    "title": "Al borrar, eliges de quién",
                    "desc": "Si un alimento lo tenéis los dos, al borrarlo decides: para los dos, solo el tuyo o solo el de tu pareja.",
                },
                {
                    "type": "fix",
                    "title": "El diario se actualiza al instante",
                    "desc": "Al cambiar una comida de momento del día, la tarjeta se mueve sola, sin recargar.",
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM release_notes WHERE version = '1.7'"))
