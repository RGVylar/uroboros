"""Link inventory consume logs to the diary entry that caused them

Revision ID: 0029
Revises: 0028
Create Date: 2026-07-15

Allows restoring stock automatically when the linked diary entry is deleted.
"""
from alembic import op
import sqlalchemy as sa

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inventory_logs",
        sa.Column(
            "diary_entry_id",
            sa.Integer(),
            sa.ForeignKey("diary_entries.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_inventory_logs_diary_entry", "inventory_logs", ["diary_entry_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_logs_diary_entry", table_name="inventory_logs")
    op.drop_column("inventory_logs", "diary_entry_id")
