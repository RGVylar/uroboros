"""Ollas: cocinar una vez y comer en varios días

Revision ID: 0087
Revises: 0086
Create Date: 2026-10-13

Una olla guarda sus ingredientes en crudo, para cuántas raciones da y, si
alguien la pesó, el peso cocinado. Lo comido no se guarda en la olla: son las
entradas del diario con `pot_id`.
"""

from alembic import op
import sqlalchemy as sa

revision = "0087"
down_revision = "0086"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("servings", sa.Float(), nullable=False),
        sa.Column("cooked_weight", sa.Float(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_pots_owner_id", "pots", ["owner_id"])
    op.create_index("ix_pots_partner_id", "pots", ["partner_id"])
    op.create_table(
        "pot_ingredients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pot_id", sa.Integer(), sa.ForeignKey("pots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("grams", sa.Float(), nullable=False),
    )
    op.create_index("ix_pot_ingredients_pot_id", "pot_ingredients", ["pot_id"])
    op.add_column(
        "diary_entries",
        sa.Column("pot_id", sa.Integer(), sa.ForeignKey("pots.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_diary_entries_pot_id", "diary_entries", ["pot_id"])


def downgrade() -> None:
    op.drop_index("ix_diary_entries_pot_id", "diary_entries")
    op.drop_column("diary_entries", "pot_id")
    op.drop_index("ix_pot_ingredients_pot_id", "pot_ingredients")
    op.drop_table("pot_ingredients")
    op.drop_index("ix_pots_partner_id", "pots")
    op.drop_index("ix_pots_owner_id", "pots")
    op.drop_table("pots")
