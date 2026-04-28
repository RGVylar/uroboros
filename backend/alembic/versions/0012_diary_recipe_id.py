"""Add recipe_id to diary_entries for tracking recipe usage

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('diary_entries',
        sa.Column('recipe_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_diary_entries_recipe_id',
        'diary_entries', 'recipes',
        ['recipe_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_diary_entries_recipe_id', 'diary_entries', ['recipe_id'])


def downgrade():
    op.drop_index('ix_diary_entries_recipe_id', table_name='diary_entries')
    op.drop_constraint('fk_diary_entries_recipe_id', 'diary_entries', type_='foreignkey')
    op.drop_column('diary_entries', 'recipe_id')
