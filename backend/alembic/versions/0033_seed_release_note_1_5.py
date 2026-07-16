"""Seed the first server-driven release note (v1.5)

Revision ID: 0033
Revises: 0032
Create Date: 2026-07-16

Data migration: inserts the launch note for 1.5 so the in-app changelog has
content in production as soon as `alembic upgrade head` runs — no manual SQL
step. Marked `major` so it shows even to users who muted the changelog.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0033"
down_revision = "0032"
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
            "version": "1.5",
            "title": "Duelo semanal",
            "importance": "major",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": "Duelo semanal de adherencia",
                    "desc": "Compite con tu pareja: quién cumple más sus propios objetivos cada semana. Actívalo en Amigos — solo se comparte el porcentaje, nunca el diario.",
                },
                {
                    "type": "nuevo",
                    "title": "Avisos de nueva versión",
                    "desc": "La app te avisa cuando hay una actualización disponible, con lo más destacado que trae.",
                },
                {
                    "type": "mejora",
                    "title": "Novedades configurables",
                    "desc": "Puedes silenciar estos avisos en Ajustes; los lanzamientos importantes se muestran igualmente.",
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM release_notes WHERE version = '1.5'"))
