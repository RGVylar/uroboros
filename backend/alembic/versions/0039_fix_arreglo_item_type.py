"""Fix legacy 'arreglo' item type in release notes -> 'fix'

Revision ID: 0039
Revises: 0038
Create Date: 2026-07-19

The 1.6 note (seeded in 0037) used type "arreglo", which is NOT in the app's
ChangeType literal ('nuevo'|'mejora'|'fix'). Once APP_VERSION reached >= 1.6 the
note entered the changelog response and ReleaseNoteItem validation raised a 500
on GET /release-notes. The router now normalizes item types defensively; this
migration also cleans the stored data so it is canonical. Idempotent.
"""
from alembic import op
import sqlalchemy as sa

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None

_rn = sa.table(
    "release_notes",
    sa.column("version", sa.String),
    sa.column("items", sa.JSON),
)


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.select(_rn.c.version, _rn.c.items)).all()
    for version, items in rows:
        if not items:
            continue
        changed = False
        for it in items:
            if isinstance(it, dict) and it.get("type") == "arreglo":
                it["type"] = "fix"
                changed = True
        if changed:
            bind.execute(
                _rn.update().where(_rn.c.version == version).values(items=items)
            )


def downgrade() -> None:
    # One-way data cleanup; nothing to undo.
    pass
