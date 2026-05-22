"""mood entries table

Revision ID: 0025
Revises: 0024
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = '0025'
down_revision = '0024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'mood_entries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('energy', sa.SmallInteger(), nullable=True),
        sa.Column('digestion', sa.SmallInteger(), nullable=True),
        sa.Column('mood', sa.SmallInteger(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.UniqueConstraint('user_id', 'entry_date', name='uq_mood_user_date'),
    )
    op.create_index('ix_mood_entries_user_date', 'mood_entries', ['user_id', 'entry_date'])


def downgrade() -> None:
    op.drop_index('ix_mood_entries_user_date', 'mood_entries')
    op.drop_table('mood_entries')
