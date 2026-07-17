"""Seed the release note for 1.6 (pareja vs amigo)

Revision ID: 0037
Revises: 0036
Create Date: 2026-07-17

Data migration, same shape as 0033. Marked `major` because this one reorganises
the Amigos screen and changes what a new friend can do by default — people will
notice, and they should hear it from us rather than find out.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0037"
down_revision = "0036"
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
            "version": "1.6",
            "title": "Pareja y amigos, por fin separados",
            "importance": "major",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": "Ahora eliges: pareja o amigo",
                    "desc": "Al añadir a alguien dices qué sois. La pareja comparte despensa y lista de la compra; los amigos, recetas y duelo. Si ya compartíais despensa, sois pareja y no tienes que hacer nada.",
                },
                {
                    "type": "nuevo",
                    "title": "Recetas para quien tú quieras",
                    "desc": "Cada receta elige su círculo: privada 🔒, solo tu pareja 💚 o tus amigos 🔗. Las que ya compartías siguen visibles para tus amigos, como hasta ahora.",
                },
                {
                    "type": "mejora",
                    "title": "Nadie entra en tu diario sin permiso",
                    "desc": "Las solicitudes nuevas ya no dan permiso para apuntar comida en tu diario: ahora se concede a mano. Los permisos que ya diste siguen tal cual — revísalos en Amigos si quieres.",
                },
                {
                    "type": "arreglo",
                    "title": "La despensa ya no se descuadra",
                    "desc": "Al dejar de compartir despensa, las cantidades podían duplicarse. Ya no.",
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM release_notes WHERE version = '1.6'"))
