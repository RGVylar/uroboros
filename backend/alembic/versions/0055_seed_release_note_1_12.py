"""Seed the release note for 1.12 (unidades, cheat days con tope, vista previa del día)

Revision ID: 0055
Revises: 0054
Create Date: 2026-09-13

Data migration, misma forma que 0050. Recoge todo lo visible desde la 1.11
(29 de julio): mes y medio de cambios sin nota, con lo que el aviso de
"hay una versión nueva" no le saltaba a nadie en Android aunque el APK
fuera de hoy. El escaneo de tickets sigue tras feature flag y no se anuncia.

Marcada `minor`: mejoras de uso, nada que cambie reglas sociales ni datos que
otras personas ven.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0055"
down_revision = "0054"
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
            "version": "1.12",
            "title": {
                "es": "Por unidades, y sin pasarse de cheat days",
                "en": "By the piece, and cheat days within limits",
                "pt": "À unidade, e sem abusar dos cheat days",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Productos en gramos, mililitros o unidades",
                        "en": "Products in grams, millilitres or pieces",
                        "pt": "Produtos em gramas, mililitros ou unidades",
                    },
                    "desc": {
                        "es": "Al crear o editar un producto eliges en qué se mide. Un huevo se registra como «1 ud» con sus macros por unidad, y un zumo pide kcal por 100 ml, no por 100 g.",
                        "en": "When you create or edit a product you pick how it's measured. An egg is logged as “1 pc” with per-piece macros, and a juice asks for kcal per 100 ml, not per 100 g.",
                        "pt": "Ao criar ou editar um produto escolhes em que se mede. Um ovo regista-se como «1 un» com os macros por unidade, e um sumo pede kcal por 100 ml, não por 100 g.",
                    },
                },
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Cheat days con tope semanal",
                        "en": "Cheat days with a weekly cap",
                        "pt": "Cheat days com limite semanal",
                    },
                    "desc": {
                        "es": "Por defecto uno a la semana (de lunes a domingo). En Ajustes puedes subirlo a 2, 3 o sin límite. La tarjeta del diario te dice cuántos llevas.",
                        "en": "One a week by default (Monday to Sunday). In Settings you can raise it to 2, 3 or no limit. The diary card shows how many you've used.",
                        "pt": "Por defeito um por semana (de segunda a domingo). Em Definições podes subir para 2, 3 ou sem limite. O cartão do diário diz quantos levas.",
                    },
                },
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Ver cómo queda el día antes de registrar",
                        "en": "See how your day ends up before logging",
                        "pt": "Ver como fica o dia antes de registar",
                    },
                    "desc": {
                        "es": "En el detalle de un alimento, una tarjeta con lo que ya llevas y cómo quedarías respecto a tu objetivo, con aviso si te pasas. Si registras para tu pareja, ves también su día.",
                        "en": "On a food's detail, a card with what you've had so far and where you'd end up against your goal, with a warning if you'd go over. Logging for your partner shows their day too.",
                        "pt": "No detalhe de um alimento, um cartão com o que já levas e como ficarias face ao teu objetivo, com aviso se passares. Se registas para o teu par, vês também o dia dele.",
                    },
                },
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Copiar un alimento de otro día a hoy",
                        "en": "Copy a food from another day to today",
                        "pt": "Copiar um alimento de outro dia para hoje",
                    },
                    "desc": {
                        "es": "Abre una entrada de un día pasado y toca «Copiar a hoy». Ajusta cantidad y comida antes de copiar.",
                        "en": "Open an entry from a past day and tap “Copy to today”. Adjust amount and meal before copying.",
                        "pt": "Abre uma entrada de um dia passado e toca em «Copiar para hoje». Ajusta quantidade e refeição antes de copiar.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Añadir comida desde el ordenador",
                        "en": "Add food from your computer",
                        "pt": "Adicionar comida a partir do computador",
                    },
                    "desc": {
                        "es": "El menú lateral tiene ahora el botón «Añadir comida». Y en Ajustes → Novedades ves qué versión tienes y si hay una más nueva, con el botón para actualizar.",
                        "en": "The side menu now has an “Add food” button. And under Settings → What's new you can see which version you're on and whether there's a newer one, with the button to update.",
                        "pt": "O menu lateral tem agora o botão «Adicionar comida». E em Definições → Novidades vês que versão tens e se há uma mais recente, com o botão para atualizar.",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "Copiar el día ya funciona en el iPhone",
                        "en": "Copying the day now works on iPhone",
                        "pt": "Copiar o dia já funciona no iPhone",
                    },
                    "desc": {
                        "es": "En Safari el botón se quedaba en «Copiando…» para siempre. Ya no.",
                        "en": "In Safari the button got stuck on “Copying…” forever. Not any more.",
                        "pt": "No Safari o botão ficava em «A copiar…» para sempre. Já não.",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "Tu constancia: el puesto ya no miente",
                        "en": "Your consistency: the rank no longer lies",
                        "pt": "A tua constância: a posição já não mente",
                    },
                    "desc": {
                        "es": "Con poca gente se enseña la posición exacta, los empates comparten puesto, y una semana con menos gente registrando ya no inventa una bajada.",
                        "en": "With few people you see your exact position, ties share a rank, and a week with fewer people logging no longer invents a drop.",
                        "pt": "Com pouca gente mostra-se a posição exata, os empates partilham posição, e uma semana com menos gente a registar já não inventa uma descida.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.12'")
