"""Seed the release note for 1.26 (bienvenida más clara)

Revision ID: 0077
Revises: 0076
Create Date: 2026-10-06

Data migration, misma forma que 0076. Va como `minor`: son arreglos de la
bienvenida y de invitar a la pareja, nada que alguien vaya a buscar y no
encuentre.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0077"
down_revision = "0076"
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
            "version": "1.26",
            "title": {
                "es": "Una bienvenida más clara",
                "en": "A clearer welcome",
                "pt": "Umas boas-vindas mais claras",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "Peso, altura y edad a mano",
                        "en": "Type your weight, height and age",
                        "pt": "Peso, altura e idade à mão",
                    },
                    "desc": {
                        "es": "Toca el número para escribirlo, y los deslizadores ya no saltan al cogerlos.",
                        "en": "Tap the number to type it, and the sliders no longer jump when you grab them.",
                        "pt": "Toca no número para o escrever, e os deslizadores já não saltam quando lhes pegas.",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "Invitar a tu pareja desde el inicio",
                        "en": "Invite your partner from the start",
                        "pt": "Convidar o teu par desde o início",
                    },
                    "desc": {
                        "es": "El botón de la bienvenida te lleva directo a invitarla, con Pareja ya elegido.",
                        "en": "The button in the welcome takes you straight to inviting them, with Partner already picked.",
                        "pt": "O botão das boas-vindas leva-te direto a convidá-lo, com Par já escolhido.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Menos ruido el primer día",
                        "en": "Less noise on day one",
                        "pt": "Menos ruído no primeiro dia",
                    },
                    "desc": {
                        "es": "Quien acaba de llegar ya no ve notas de versiones antiguas ni el botón de copiar el día de ayer, y tu plan se explica sin tecnicismos.",
                        "en": "Newcomers no longer see notes from old versions or the copy-yesterday button, and your plan is explained without jargon.",
                        "pt": "Quem acabou de chegar já não vê notas de versões antigas nem o botão de copiar o dia de ontem, e o teu plano explica-se sem tecnicismos.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.26'")
