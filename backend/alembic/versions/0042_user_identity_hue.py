"""Add users.identity_hue

Revision ID: 0042
Revises: 0041
Create Date: 2026-07-22

Identity colour (OKLCH hue) each user picks in their profile. Shown as the avatar
ring and the tint of their rows when a partner intercalates their day into the
diary. Nullable: null falls back to the name-derived hue Avatar.svelte already
computes, so existing rows need no backfill.
"""
from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS: the app also runs Base.metadata.create_all() on startup, so
    # on a fresh DB the column may already exist when this migration runs.
    # Postgres (prod) supports it; migrations don't run against the SQLite test DB.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS identity_hue INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS identity_hue")
