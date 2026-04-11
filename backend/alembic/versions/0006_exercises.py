"""Add exercise tracking

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id                  SERIAL PRIMARY KEY,
            user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name                VARCHAR(255) NOT NULL,
            kcal_per_unit       FLOAT NOT NULL,
            unit                VARCHAR(50) NOT NULL,
            created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS ix_exercises_user_id ON exercises(user_id);

        CREATE TABLE IF NOT EXISTS exercise_sessions (
            id                  SERIAL PRIMARY KEY,
            user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_date        DATE NOT NULL,
            total_calories      FLOAT NOT NULL DEFAULT 0,
            created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_exercise_sessions_user_date UNIQUE (user_id, session_date)
        );

        CREATE INDEX IF NOT EXISTS ix_exercise_sessions_user_id ON exercise_sessions(user_id);
        CREATE INDEX IF NOT EXISTS ix_exercise_sessions_session_date ON exercise_sessions(session_date);

        CREATE TABLE IF NOT EXISTS exercise_session_entries (
            id                  SERIAL PRIMARY KEY,
            session_id          INTEGER NOT NULL REFERENCES exercise_sessions(id) ON DELETE CASCADE,
            exercise_id         INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
            quantity            FLOAT NOT NULL,
            calories            FLOAT NOT NULL,
            created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS ix_exercise_session_entries_session_id ON exercise_session_entries(session_id);
        CREATE INDEX IF NOT EXISTS ix_exercise_session_entries_exercise_id ON exercise_session_entries(exercise_id);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS exercise_session_entries;
        DROP TABLE IF EXISTS exercise_sessions;
        DROP TABLE IF EXISTS exercises;
    """)
