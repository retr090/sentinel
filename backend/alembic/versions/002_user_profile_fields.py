"""Add avatar_url and force_password_change to users

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('avatar_url', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('force_password_change', sa.Boolean(),
                                     nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('users', 'force_password_change')
    op.drop_column('users', 'avatar_url')
