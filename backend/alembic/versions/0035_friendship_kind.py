"""Friendship kind: partner vs friend

Revision ID: 0035
Revises: 0034
Create Date: 2026-07-17

Until now "pareja" only existed in the marketing copy and in comments: the model
just had a Friendship with loose flags, so the household features (shared
inventory + shopping list) — which only make sense with one person — sat on top
of an N:N relationship that never stopped you from having two.

Backfill rule: an active shared inventory is the only trustworthy signal of
living together, because it takes a deliberate toggle from *each* side.
`can_add_food` is worthless here — it is server_default true on every request
sent, so it says nothing about intent.
"""
from alembic import op
import sqlalchemy as sa

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    kind = sa.Enum("friend", "partner", name="friendship_kind")
    kind.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "friendships",
        sa.Column("kind", kind, nullable=False, server_default="friend"),
    )
    op.add_column(
        "friendships",
        sa.Column(
            "partner_proposed_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE friendships
        SET kind = 'partner'
        WHERE status = 'accepted'
          AND shared_inventory_requester
          AND shared_inventory_receiver
        """
    )

    # can_add_food defaulted to true, so every request ever sent quietly granted
    # the sender write access to the other person's diary. New rows now start
    # false. Existing grants are deliberately left alone: some are in daily use,
    # and there is no way to tell which — diary_entries records whose entry it is,
    # never who wrote it.
    op.alter_column("friendships", "can_add_food", server_default=sa.false())

    # One partner per user. These two indexes stop you being the requester of two
    # partnerships, or the receiver of two — but not the requester of one and the
    # receiver of another, because a unique index yields one entry per row and a
    # row has two participants. That gap is closed in the router. Sealing it here
    # would take an EXCLUDE constraint over a generated participants array, which
    # is a lot of machinery for an app whose whole friendships table is 3 rows.
    op.create_index(
        "uq_partner_requester",
        "friendships",
        ["requester_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'partner'"),
    )
    op.create_index(
        "uq_partner_receiver",
        "friendships",
        ["receiver_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'partner'"),
    )


def downgrade() -> None:
    op.alter_column("friendships", "can_add_food", server_default=sa.true())
    op.drop_index("uq_partner_receiver", table_name="friendships")
    op.drop_index("uq_partner_requester", table_name="friendships")
    op.drop_column("friendships", "partner_proposed_by")
    op.drop_column("friendships", "kind")
    sa.Enum(name="friendship_kind").drop(op.get_bind(), checkfirst=True)
