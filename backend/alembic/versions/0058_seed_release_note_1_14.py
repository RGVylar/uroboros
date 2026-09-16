"""Seed the release note for 1.14 (duelo con puntos por día)

Revision ID: 0058
Revises: 0057
Create Date: 2026-09-16

Data migration, misma forma que 0057. La adherencia deja de ser acierto/fallo
y pasa a puntuar cada día (calorías + proteína); eso cambia el número que ve
todo el mundo en el duelo, en «Tu constancia» y en las medallas, así que va
como `major`: quien abra la app tiene que enterarse de por qué su semana ya
no marca lo mismo.
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0058"
down_revision = "0057"
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
            "version": "1.14",
            "title": {
                "es": "El duelo ahora puntúa",
                "en": "The duel now keeps score",
                "pt": "O duelo agora pontua",
            },
            "importance": "major",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Cada día vale hasta 100 puntos",
                        "en": "Each day is worth up to 100 points",
                        "pt": "Cada dia vale até 100 pontos",
                    },
                    "desc": {
                        "es": "Ya no es cumplir o no cumplir: 70 puntos por acercarte a tus calorías (clavarlas a 20 kcal no vale lo mismo que pasarte 240) y 30 por llegar a tu proteína. Tu semana es la media de tus días, y ese mismo número manda en el duelo, en «Tu constancia» y en las medallas.",
                        "en": "It's no longer hit or miss: 70 points for getting close to your calories (nailing them within 20 kcal isn't the same as going 240 over) and 30 for reaching your protein. Your week is the average of your days, and that same number drives the duel, “Your consistency” and the medals.",
                        "pt": "Já não é cumprir ou não cumprir: 70 pontos por te aproximares das tuas calorias (acertar a 20 kcal não vale o mesmo que passar 240) e 30 por chegares à tua proteína. A tua semana é a média dos teus dias, e é esse número que manda no duelo, em «A tua constância» e nas medalhas.",
                    },
                },
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Ve por qué un día vale lo que vale",
                        "en": "See why a day scored what it did",
                        "pt": "Vê porque é que um dia vale o que vale",
                    },
                    "desc": {
                        "es": "En el duelo, cada día muestra sus puntos y una flecha si te pasaste (↑) o te quedaste corto (↓) de calorías. Toca un día y verás el desglose: cuánto te desviaste y cuánta proteína llegaste a comer.",
                        "en": "In the duel, each day shows its points and an arrow if you went over (↑) or fell short (↓) on calories. Tap a day to see the breakdown: how far off you were and how much protein you got.",
                        "pt": "No duelo, cada dia mostra os seus pontos e uma seta se passaste (↑) ou ficaste curto (↓) nas calorias. Toca num dia e vês o detalhe: quanto te desviaste e quanta proteína comeste.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Medallas del perfil sobre el ranking global",
                        "en": "Profile medals from the global ranking",
                        "pt": "Medalhas do perfil no ranking global",
                    },
                    "desc": {
                        "es": "El oro, la plata y el bronce del perfil salen de tu puesto entre todos los usuarios activos de la semana, igual que «Tu constancia». Quedar en el podio es la medalla, sin más condiciones. Sin nombres: solo tu posición.",
                        "en": "Gold, silver and bronze on your profile come from your place among everyone active that week, same as “Your consistency”. Making the podium is the medal, no strings attached. No names — just your position.",
                        "pt": "O ouro, a prata e o bronze do perfil saem da tua posição entre todos os utilizadores ativos da semana, tal como «A tua constância». Ficar no pódio é a medalha, sem mais condições. Sem nomes: só a tua posição.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.14'")
