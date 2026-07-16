"""Server-driven changelog

Revision ID: 0031
Revises: 0030
Create Date: 2026-07-16

Adds the `release_notes` table (patch notes served from the DB, so the text and
the trigger no longer live in the frontend bundle) and a `changelog_opt_out`
preference on users for muting the in-app changelog.
"""
from alembic import op
import sqlalchemy as sa

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "release_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("importance", sa.String(length=10), nullable=False, server_default="minor"),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("version", name="uq_release_notes_version"),
    )
    op.add_column(
        "users",
        sa.Column("changelog_opt_out", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "changelog_opt_out")
    op.drop_table("release_notes")
