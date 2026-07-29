"""Add friendships.blocked_by

Revision ID: 0049
Revises: 0048
Create Date: 2026-07-29

Bloquear a alguien. La política de contenido generado por usuarios de Play lo
exige en cuanto una persona puede enseñarle una imagen a otra, y desde que hay
fotos de perfil ese es el caso.

La fila de la amistad NO se borra al bloquear: se queda con blocked_by puesto,
y el UNIQUE de (requester_id, receiver_id) es lo que impide que la persona
bloqueada mande una solicitud nueva. Borrarla dejaría el hueco libre.
"""
from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE friendships ADD COLUMN IF NOT EXISTS blocked_by INTEGER")
    op.execute(
        "ALTER TABLE friendships ADD CONSTRAINT fk_friendships_blocked_by "
        "FOREIGN KEY (blocked_by) REFERENCES users (id)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE friendships DROP CONSTRAINT IF EXISTS fk_friendships_blocked_by")
    op.execute("ALTER TABLE friendships DROP COLUMN IF EXISTS blocked_by")
