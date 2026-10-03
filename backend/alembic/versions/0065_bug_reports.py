"""Add bug_reports

Revision ID: 0065
Revises: 0064
Create Date: 2026-10-03

Informes de problemas enviados desde Ajustes, con la versión y la plataforma
que pone la app sola. La captura opcional no se guarda: va a Telegram y ya.
"""
from alembic import op
import sqlalchemy as sa

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bug_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("app_version", sa.String(16), nullable=False, server_default=""),
        sa.Column("platform", sa.String(16), nullable=False, server_default=""),
        sa.Column("device", sa.String(255), nullable=False, server_default=""),
        sa.Column("locale", sa.String(8), nullable=False, server_default=""),
        sa.Column("route", sa.String(128), nullable=False, server_default=""),
        sa.Column("had_screenshot", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bug_reports_user_id", "bug_reports", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_bug_reports_user_id", table_name="bug_reports")
    op.drop_table("bug_reports")
