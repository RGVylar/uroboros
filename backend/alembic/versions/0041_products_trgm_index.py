"""pg_trgm GIN indexes on products(name, brand) for ILIKE '%q%' search

Revision ID: 0041
Revises: 0040
Create Date: 2026-07-19

/products?q= runs on every keystroke (350 ms debounce) and does
`name ILIKE '%q%' OR brand ILIKE '%q%'`, which a plain B-tree index can't
serve — leading '%' rules out a prefix scan. pg_trgm + a GIN trigram index
lets Postgres use a bitmap index scan instead of a seq scan.

Postgres only: SQLite (used for the demo/test DB, see app/database.py) has no
pg_trgm equivalent and doesn't need it at the current table size, and
CREATE EXTENSION requires a privilege SQLite has no concept of. Guarded so
`alembic upgrade head` stays a no-op there, matching the dialect-guard
pattern used in 0003/0014/0015/0016/0017.

Also requires the pg_trgm extension to be installed/available on the target
Postgres (superuser or preloaded extension) — verify in the deploy env before
running against production.
"""
from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_name_trgm ON products USING gin (name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_brand_trgm ON products USING gin (brand gin_trgm_ops)"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP INDEX IF EXISTS ix_products_brand_trgm")
    op.execute("DROP INDEX IF EXISTS ix_products_name_trgm")
