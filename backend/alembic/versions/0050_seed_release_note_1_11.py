"""Seed the release note for 1.11 (foto de perfil + código de invitación + denunciar)

Revision ID: 0050
Revises: 0049
Create Date: 2026-07-29

Data migration, misma forma que 0043/0044/0045 pero con los textos ya en el
formato i18n que introdujo 0046 (`{"es": ..., "en": ..., "pt": ...}`).

Marcada `major`: cambia cómo se añade a la gente (antes por email, ahora por
código) y añade una foto que otras personas van a ver. Quien tenga silenciadas
las novedades menores también necesita enterarse de esto.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0050"
down_revision = "0049"
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
            "version": "1.11",
            "title": {
                "es": "Tu cara, si quieres",
                "en": "Your face, if you want",
                "pt": "A tua cara, se quiseres",
            },
            "importance": "major",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Sube tu propia foto de perfil",
                        "en": "Upload your own profile photo",
                        "pt": "Carrega a tua própria foto de perfil",
                    },
                    "desc": {
                        "es": "En tu perfil, toca el avatar y elige «Subir una foto». Solo la ven las personas cuya solicitud has aceptado, nunca aparece en una solicitud pendiente. Al subirla le borramos los datos de ubicación que traen las fotos del móvil. Los 18 avatares de siempre siguen ahí.",
                        "en": "In your profile, tap your avatar and pick “Upload a photo”. Only people whose request you've accepted can see it — it never shows up on a pending request. We strip the location data that phone photos carry. The usual 18 avatars are still there.",
                        "pt": "No teu perfil, toca no avatar e escolhe «Carregar uma foto». Só a veem as pessoas cujo pedido aceitaste, nunca aparece num pedido pendente. Ao carregá-la apagamos os dados de localização que as fotos do telemóvel trazem. Os 18 avatares de sempre continuam lá.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Ahora se añade gente por código, no por email",
                        "en": "Add people by code now, not by email",
                        "pt": "Agora adicionam-se pessoas por código, não por email",
                    },
                    "desc": {
                        "es": "Tienes un código de ocho caracteres en «Amigos → Añadir». Enséñalo o cópialo a quien quieras que te añada. Ya no hace falta dar tu email, y nadie puede encontrarte sin el código.",
                        "en": "You now have an eight-character code under “Friends → Add”. Show it or copy it to whoever you want to be added by. You no longer need to hand out your email, and nobody can find you without the code.",
                        "pt": "Tens um código de oito caracteres em «Amigos → Adicionar». Mostra-o ou copia-o a quem quiseres que te adicione. Já não precisas de dar o teu email, e ninguém te encontra sem o código.",
                    },
                },
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Denunciar y bloquear",
                        "en": "Report and block",
                        "pt": "Denunciar e bloquear",
                    },
                    "desc": {
                        "es": "Cada persona de tu lista tiene un botón «Denunciar». La revisamos y la relación queda bloqueada al momento: dejáis de veros y no podéis volver a enviaros solicitudes.",
                        "en": "Everyone on your list has a “Report” button. We review it and the relationship is blocked right away: you stop seeing each other and can't send requests again.",
                        "pt": "Cada pessoa da tua lista tem um botão «Denunciar». Revemo-la e a relação fica bloqueada de imediato: deixam de se ver e não podem voltar a enviar pedidos.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.11'")
