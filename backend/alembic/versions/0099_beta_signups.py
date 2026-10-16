"""Apuntados a la beta desde /beta

Revision ID: 0099
Revises: 0098
Create Date: 2026-10-16

La prueba cerrada de Play necesita 12 testers con Android y cada uno hay que
meterlo a mano en la lista de emails de Play Console. Hasta ahora se recogían
respondiendo a una historia de Instagram; la página /beta los guarda aquí.
"""

from alembic import op
import sqlalchemy as sa

revision = "0099"
down_revision = "0098"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "beta_signups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(80), nullable=False, server_default=""),
        sa.Column("lang", sa.String(8), nullable=False, server_default="es"),
        sa.Column("added", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("beta_signups")
