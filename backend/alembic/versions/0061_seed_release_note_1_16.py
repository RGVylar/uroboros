"""Seed the release note for 1.16 (historial honesto, búsqueda limpia, lista de la compra)

Revision ID: 0061
Revises: 0060
Create Date: 2026-09-26

Data migration, misma forma que 0059. Arreglos y pulido sin nada que cambie
cómo se usa la app, así que va como `minor`.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0061"
down_revision = "0060"
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
            "version": "1.16",
            "title": {
                "es": "Menos ruido, más claro",
                "en": "Less noise, more clarity",
                "pt": "Menos ruído, mais claro",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "mejora",
                    "title": {
                        "es": "El historial ya no cuenta los días en blanco",
                        "en": "History no longer counts blank days",
                        "pt": "O histórico já não conta os dias em branco",
                    },
                    "desc": {
                        "es": "Un día sin registrar no es ni déficit ni fallo: queda fuera de la media y de la adherencia, que ahora puntúa igual que el duelo. Los días vacíos seguidos se agrupan en una línea.",
                        "en": "A day you didn't log is neither a deficit nor a miss: it's left out of the average and of adherence, which now scores the same way as the duel. Consecutive empty days are grouped into one line.",
                        "pt": "Um dia sem registos não é défice nem falha: fica fora da média e da adesão, que agora pontua como o duelo. Os dias vazios seguidos agrupam-se numa linha.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Búsqueda sin productos a 0 kcal",
                        "en": "Search without 0 kcal products",
                        "pt": "Pesquisa sem produtos a 0 kcal",
                    },
                    "desc": {
                        "es": "Los productos que traían la energía solo en kJ salían a 0 kcal; ahora se calculan bien. Los que no tienen ningún dato ya no aparecen, y el mismo producto en varios formatos sale una sola vez.",
                        "en": "Products that only listed energy in kJ showed up at 0 kcal; now they're calculated properly. Products with no data at all no longer appear, and the same product in several sizes shows up only once.",
                        "pt": "Os produtos que só traziam a energia em kJ apareciam a 0 kcal; agora calculam-se bem. Os que não têm nenhum dado já não aparecem, e o mesmo produto em vários formatos aparece só uma vez.",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "La lista de la compra vuelve a funcionar",
                        "en": "The shopping list works again",
                        "pt": "A lista de compras volta a funcionar",
                    },
                    "desc": {
                        "es": "Daba error al abrirla, añadir o marcar productos.",
                        "en": "It failed when opening it, adding items or ticking them off.",
                        "pt": "Dava erro ao abri-la, adicionar ou marcar produtos.",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "La barra inferior ya no tapa nada",
                        "en": "The bottom bar no longer covers anything",
                        "pt": "A barra inferior já não tapa nada",
                    },
                    "desc": {
                        "es": "Deja sitio al final de cada pantalla y se esconde mientras escribes, para que no quede encima de los resultados.",
                        "en": "It leaves room at the end of every screen and hides while you type, so it doesn't sit on top of the results.",
                        "pt": "Deixa espaço no fim de cada ecrã e esconde-se enquanto escreves, para não ficar por cima dos resultados.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.16'")
