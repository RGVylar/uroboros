"""Seed the release note for 1.10 (copiar comida de otro día + iconos del diario)

Revision ID: 0045
Revises: 0044
Create Date: 2026-07-25

Data migration, misma forma que 0037/0038/0043/0044. Marcada `minor`: es un
botón nuevo que solo aparece al mirar un día pasado (no cambia nada por
defecto) más pulido visual de iconos ya existentes, así que respeta el
opt-out de novedades menores.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0045"
down_revision = "0044"
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
            "version": "1.10",
            "title": "Copia una comida de otro día",
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": "Repite una comida de un día anterior",
                    "desc": "Al mirar un día pasado, cada comida tiene un botón para copiarla a hoy tal cual. Útil cuando vuelves a comer algo que ya registraste hace unos días.",
                },
                {
                    "type": "mejora",
                    "title": "Iconos más claros en el diario",
                    "desc": "Los botones de copiar, guardar como receta y vaciar comida pasan a iconos, así no se corta el texto en pantallas estrechas.",
                },
                {
                    "type": "mejora",
                    "title": "El icono de Recetas, coherente",
                    "desc": "El mismo libro se usa ahora en la barra de navegación y en el menú lateral.",
                },
                {
                    "type": "nuevo",
                    "title": "Widgets en la pantalla de inicio (Android)",
                    "desc": "Acceso rápido para apuntar comida y un widget con código QR para invitar, directo desde el escritorio del móvil.",
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM release_notes WHERE version = '1.10'"))
