"""Add users.invite_code

Revision ID: 0047
Revises: 0046
Create Date: 2026-07-29

Código de invitación por usuario, para añadir amigos sin dar el email. Nullable
y sin backfill: lo genera app/invite_codes.py la primera vez que cada usuario
pide el suyo, así que esta migración solo abre el hueco y el índice único.
"""
from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS: la app también ejecuta Base.metadata.create_all() al
    # arrancar, así que en una BD nueva la columna puede existir ya.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_code VARCHAR(12)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_invite_code ON users (invite_code)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_invite_code")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS invite_code")
