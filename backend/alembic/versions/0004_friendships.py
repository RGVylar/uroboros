"""Add friendships table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE friendship_status AS ENUM ('pending', 'accepted', 'rejected');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;

        CREATE TABLE IF NOT EXISTS friendships (
            id          SERIAL PRIMARY KEY,
            requester_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            receiver_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status       friendship_status NOT NULL DEFAULT 'pending',
            can_add_food BOOLEAN NOT NULL DEFAULT true,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_friendship_pair UNIQUE (requester_id, receiver_id)
        );

        CREATE INDEX IF NOT EXISTS ix_friendships_requester_id ON friendships(requester_id);
        CREATE INDEX IF NOT EXISTS ix_friendships_receiver_id  ON friendships(receiver_id);
        CREATE INDEX IF NOT EXISTS ix_friendships_receiver_status ON friendships(receiver_id, status);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS friendships CASCADE;
        DROP TYPE IF EXISTS friendship_status;
    """)
