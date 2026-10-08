"""Versión, plataforma y última conexión de cada usuario

Revision ID: 0082
Revises: 0081
Create Date: 2026-10-08

Las rellena GET /release-notes, que la app llama cada vez que arranca. Sirven
para saber cuánta gente sigue en una APK vieja y para el resumen semanal de
Telegram. Quien no haya abierto la app desde este cambio se queda vacío.
"""

from alembic import op
import sqlalchemy as sa

revision = "0082"
down_revision = "0081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("app_version", sa.String(16), nullable=False, server_default=""))
    op.add_column("users", sa.Column("platform", sa.String(16), nullable=False, server_default=""))
    op.add_column("users", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_seen_at")
    op.drop_column("users", "platform")
    op.drop_column("users", "app_version")
