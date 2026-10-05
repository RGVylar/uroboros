"""Seed the release note for 1.20 (diagnóstico de pasos y recordatorios)

Revision ID: 0069
Revises: 0068
Create Date: 2026-10-05

Data migration, misma forma que 0068. Una herramienta de Ajustes y un arreglo
de recordatorios, solo en Android: va como `minor`.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0069"
down_revision = "0068"
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
            "version": "1.20",
            "title": {
                "es": "Pasos y recordatorios en Android",
                "en": "Steps and reminders on Android",
                "pt": "Passos e lembretes no Android",
            },
            "importance": "minor",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Diagnóstico en Ajustes",
                        "en": "Diagnostics in Settings",
                        "pt": "Diagnóstico nas Definições",
                    },
                    "desc": {
                        "es": "Si los pasos no aparecen o no te llegan los recordatorios, pulsa Ajustes → Diagnóstico: te dice qué falla y cómo arreglarlo, y nos llega a nosotros para ayudarte.",
                        "en": "If your steps don't show up or reminders never arrive, tap Settings → Diagnostics: it tells you what's wrong and how to fix it, and lets us know so we can help.",
                        "pt": "Se os passos não aparecem ou os lembretes não chegam, toca em Definições → Diagnóstico: diz-te o que falha e como resolver, e chega-nos a nós para te ajudarmos.",
                    },
                },
                {
                    "type": "fix",
                    "title": {
                        "es": "Recordatorios al activarlos desde el aviso",
                        "en": "Reminders when turned on from the prompt",
                        "pt": "Lembretes ao ativá-los a partir do aviso",
                    },
                    "desc": {
                        "es": "Si activabas las notificaciones desde el aviso de la portada, los recordatorios no se programaban hasta cerrar del todo la app. Ahora empiezan al momento.",
                        "en": "If you turned on notifications from the prompt on the home screen, reminders weren't scheduled until the app was fully closed. Now they start right away.",
                        "pt": "Se ativavas as notificações a partir do aviso no ecrã inicial, os lembretes só eram agendados depois de fechar a app por completo. Agora começam logo.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.20'")
