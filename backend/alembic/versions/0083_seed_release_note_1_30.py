"""Seed the release note for 1.30 (la app funciona de verdad sin conexión)

Revision ID: 0083
Revises: 0082
Create Date: 2026-10-08

Data migration, misma forma que 0081. Va como `minor`: pensada para los
bloqueos del fútbol (la PWA abre sin red, búsqueda de genéricos y de lo ya
usado sin conexión, lo apuntado se ve al momento y se envía solo).
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0083"
down_revision = "0082"
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
            "version": "1.30",
            "title": {
                "es": "Sin conexión, sin problema",
                "en": "Offline, no problem",
                "pt": "Sem ligação, sem problema",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "La app abre aunque no haya conexión",
                        "en": "The app opens even without a connection",
                        "pt": "A app abre mesmo sem ligação",
                    },
                    "desc": {
                        "es": "Durante los partidos de fútbol algunos operadores bloquean la conexión con uroboros. Ahora la app abre igual, con tu diario de hoy, y puedes seguir apuntando.",
                        "en": "During football matches some Spanish carriers block the connection to uroboros. The app now opens anyway, with today's diary, and you can keep logging.",
                        "pt": "Durante os jogos de futebol alguns operadores em Espanha bloqueiam a ligação ao uroboros. Agora a app abre na mesma, com o diário de hoje, e podes continuar a registar.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Buscar sin conexión",
                        "en": "Search while offline",
                        "pt": "Pesquisar sem ligação",
                    },
                    "desc": {
                        "es": "El buscador encuentra los alimentos genéricos (pollo, arroz, plátano…) y los que ya has usado aunque no haya conexión.",
                        "en": "Search finds generic foods (chicken, rice, banana…) and the ones you've already used, even without a connection.",
                        "pt": "A pesquisa encontra os alimentos genéricos (frango, arroz, banana…) e os que já usaste, mesmo sem ligação.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Lo que apuntas se ve al momento",
                        "en": "What you log shows up right away",
                        "pt": "O que registas aparece logo",
                    },
                    "desc": {
                        "es": "Sin conexión, las comidas, el agua y los suplementos aparecen en el diario en cuanto los apuntas y se envían solos al volver la conexión, aunque hayas cerrado la app.",
                        "en": "While offline, meals, water and supplements appear in your diary as soon as you log them and are sent automatically once you're back online, even if you closed the app.",
                        "pt": "Sem ligação, as refeições, a água e os suplementos aparecem no diário assim que os registas e são enviados sozinhos quando a ligação voltar, mesmo que tenhas fechado a app.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.30'")
