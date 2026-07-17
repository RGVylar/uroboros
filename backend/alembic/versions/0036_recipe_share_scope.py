"""Recipe share scope: none / partner / friends

Revision ID: 0036
Revises: 0035
Create Date: 2026-07-17

`is_shared` was all-or-nothing: switching it on published the recipe to every
accepted friend, with no way to keep one between partners. Now that a friendship
has a kind, a recipe can pick its circle.

Backfill keeps the status quo — anything shared today becomes 'friends', which is
exactly who can already see it. Nobody loses access on deploy; narrowing a recipe
to the partner is a choice the owner makes afterwards.
"""
from alembic import op
import sqlalchemy as sa

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    scope = sa.Enum("none", "partner", "friends", name="recipe_scope")
    scope.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "recipes",
        sa.Column("share_scope", scope, nullable=False, server_default="none"),
    )
    op.execute("UPDATE recipes SET share_scope = 'friends' WHERE is_shared")
    op.drop_column("recipes", "is_shared")


def downgrade() -> None:
    op.add_column(
        "recipes",
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE recipes SET is_shared = true WHERE share_scope <> 'none'")
    op.drop_column("recipes", "share_scope")
    sa.Enum(name="recipe_scope").drop(op.get_bind(), checkfirst=True)
