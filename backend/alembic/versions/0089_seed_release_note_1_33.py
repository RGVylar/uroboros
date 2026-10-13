"""Seed the release note for 1.33 (la olla dibujada)

Revision ID: 0089
Revises: 0088
Create Date: 2026-10-13

Data migration, misma forma que 0088. Va como `minor`: es un retoque visual
de las ollas que salieron en 1.32.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0089"
down_revision = "0088"
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
            "version": "1.33",
            "title": {
                "es": "Una olla de verdad",
                "en": "A real pot",
                "pt": "Uma panela a sério",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "La olla se vacía a la vista",
                        "en": "Watch the pot empty",
                        "pt": "A panela esvazia-se à vista",
                    },
                    "desc": {
                        "es": "Las ollas se dibujan con el caldo a la altura de lo que queda, con vapor mientras quede algo. Al apuntar, lo que te llevas sale rayado en tu color, o en los dos si es para los dos.",
                        "en": "Pots are drawn with the stew at the level of what's left, steaming while there's some. When logging, what you take shows striped in your colour, or both colours if it's for both of you.",
                        "pt": "As panelas desenham-se com o caldo à altura do que resta, a fumegar enquanto houver. Ao registar, o que levas aparece às riscas na tua cor, ou nas duas se for para os dois.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.33'")
