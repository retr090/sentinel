"""add dark web monitor tables

Revision ID: a4a60f9c68da
Revises: 003
Create Date: 2026-05-16 12:17:42.914214

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a4a60f9c68da'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'darkweb_keywords',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('keyword', sa.String(length=500), nullable=False),
        sa.Column('aliases', sa.JSON(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('alert_mode', sa.String(length=20), nullable=True),
        sa.Column('sources', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('hit_count', sa.Integer(), nullable=True),
        sa.Column('last_hit', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_darkweb_keyword_active', 'darkweb_keywords', ['is_active'], unique=False)
    op.create_index('idx_darkweb_keyword_priority', 'darkweb_keywords', ['priority'], unique=False)

    op.create_table(
        'darkweb_mentions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('keyword_id', sa.UUID(), nullable=True),
        sa.Column('keyword_matched', sa.String(length=500), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('source_url', sa.String(length=2000), nullable=True),
        sa.Column('title', sa.String(length=1000), nullable=True),
        sa.Column('snippet', sa.Text(), nullable=True),
        sa.Column('full_content', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('threat_actor', sa.String(length=200), nullable=True),
        sa.Column('victim_org', sa.String(length=500), nullable=True),
        sa.Column('victim_country', sa.String(length=10), nullable=True),
        sa.Column('is_reviewed', sa.Boolean(), nullable=True),
        sa.Column('is_false_positive', sa.Boolean(), nullable=True),
        sa.Column('analyst_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_mention_discovered', 'darkweb_mentions', ['discovered_at'], unique=False)
    op.create_index('idx_mention_keyword', 'darkweb_mentions', ['keyword_matched'], unique=False)
    op.create_index('idx_mention_reviewed', 'darkweb_mentions', ['is_reviewed'], unique=False)
    op.create_index('idx_mention_severity', 'darkweb_mentions', ['severity'], unique=False)
    op.create_index('idx_mention_source', 'darkweb_mentions', ['source'], unique=False)

    op.create_table(
        'darkweb_scans',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scan_type', sa.String(length=100), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('keywords_scanned', sa.Integer(), nullable=True),
        sa.Column('mentions_found', sa.Integer(), nullable=True),
        sa.Column('new_mentions', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_scan_created', 'darkweb_scans', ['created_at'], unique=False)
    op.create_index('idx_scan_status', 'darkweb_scans', ['status'], unique=False)

    op.create_table(
        'darkweb_alerts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('mention_id', sa.UUID(), nullable=False),
        sa.Column('keyword_id', sa.UUID(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=True),
        sa.Column('acknowledged_by', sa.String(length=100), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('notification_sent', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('darkweb_alerts')
    op.drop_index('idx_scan_status', table_name='darkweb_scans')
    op.drop_index('idx_scan_created', table_name='darkweb_scans')
    op.drop_table('darkweb_scans')
    op.drop_index('idx_mention_source', table_name='darkweb_mentions')
    op.drop_index('idx_mention_severity', table_name='darkweb_mentions')
    op.drop_index('idx_mention_reviewed', table_name='darkweb_mentions')
    op.drop_index('idx_mention_keyword', table_name='darkweb_mentions')
    op.drop_index('idx_mention_discovered', table_name='darkweb_mentions')
    op.drop_table('darkweb_mentions')
    op.drop_index('idx_darkweb_keyword_priority', table_name='darkweb_keywords')
    op.drop_index('idx_darkweb_keyword_active', table_name='darkweb_keywords')
    op.drop_table('darkweb_keywords')
