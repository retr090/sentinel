"""Add risk_level, tags to IOC and create IOCBulkJob table

Revision ID: 003
Revises: 002
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('iocs', sa.Column('risk_level', sa.String(32), nullable=True, server_default='clean'))
    op.add_column('iocs', sa.Column('tags', sa.JSON(), nullable=True))

    op.create_table(
        'ioc_bulk_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending'),
        sa.Column('total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ioc_bulk_jobs_id', 'ioc_bulk_jobs', ['id'])


def downgrade():
    op.drop_index('ix_ioc_bulk_jobs_id', table_name='ioc_bulk_jobs')
    op.drop_table('ioc_bulk_jobs')
    op.drop_column('iocs', 'tags')
    op.drop_column('iocs', 'risk_level')
