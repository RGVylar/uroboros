"""Perfil corporal y semana de la propuesta en user_goals

Revision ID: 0084
Revises: 0083
Create Date: 2026-10-08

El onboarding y la calculadora de Objetivos pedían sexo, edad, altura,
actividad y objetivo y los tiraban tras calcular. Ahora se guardan: la
propuesta semanal de objetivos necesita saber si quieres perder, mantener o
ganar. `adapt_week` recuerda la semana en la que ya respondiste a la propuesta.
Las cuentas anteriores se quedan con el perfil vacío.
"""

from alembic import op
import sqlalchemy as sa

revision = "0084"
down_revision = "0083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_goals", sa.Column("sex", sa.String(8), nullable=True))
    op.add_column("user_goals", sa.Column("birth_year", sa.Integer(), nullable=True))
    op.add_column("user_goals", sa.Column("height_cm", sa.Float(), nullable=True))
    op.add_column("user_goals", sa.Column("activity", sa.String(16), nullable=True))
    op.add_column("user_goals", sa.Column("objective", sa.String(16), nullable=True))
    op.add_column("user_goals", sa.Column("adapt_week", sa.String(10), nullable=False, server_default=""))


def downgrade() -> None:
    for col in ("adapt_week", "objective", "activity", "height_cm", "birth_year", "sex"):
        op.drop_column("user_goals", col)
