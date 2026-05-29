"""darkweb search targets feeds

Revision ID: f8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-05-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f8b9c0d1e2f3'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('darkweb_mentions', sa.Column('original_query', sa.String(length=500), nullable=True))
    op.add_column('darkweb_mentions', sa.Column('effective_query', sa.String(length=700), nullable=True))
    op.add_column('darkweb_mentions', sa.Column('normalized_source_url', sa.String(length=2000), nullable=True))
    op.add_column('darkweb_mentions', sa.Column('dedup_hash', sa.String(length=64), nullable=True))
    op.add_column('darkweb_mentions', sa.Column('content_hash', sa.String(length=64), nullable=True))
    op.add_column('darkweb_mentions', sa.Column('severity_reason', sa.Text(), nullable=True))
    op.add_column('darkweb_mentions', sa.Column('triage_status', sa.String(length=30), nullable=True, server_default='new'))

    op.execute("UPDATE darkweb_mentions SET triage_status = COALESCE(triage_status, CASE WHEN is_false_positive THEN 'false_positive' WHEN is_reviewed THEN 'reviewed' ELSE 'new' END)")
    op.execute("UPDATE darkweb_mentions SET normalized_source_url = LOWER(source_url) WHERE normalized_source_url IS NULL AND source_url IS NOT NULL")
    op.execute("UPDATE darkweb_mentions SET dedup_hash = md5(COALESCE(source, '') || '|' || COALESCE(normalized_source_url, title, '') || '|' || COALESCE(snippet, '')) WHERE dedup_hash IS NULL")
    op.execute("UPDATE darkweb_mentions SET content_hash = md5(COALESCE(title, '') || E'\n' || COALESCE(snippet, '') || E'\n' || COALESCE(full_content, '')) WHERE content_hash IS NULL")

    op.create_index('idx_mention_source_url', 'darkweb_mentions', ['normalized_source_url'], unique=False)
    op.create_index('idx_mention_dedup_hash', 'darkweb_mentions', ['dedup_hash'], unique=False)
    op.create_index('idx_mention_content_hash', 'darkweb_mentions', ['content_hash'], unique=False)
    op.create_index('idx_mention_triage_status', 'darkweb_mentions', ['triage_status'], unique=False)

    op.create_table(
        'darkweb_feed_cache',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_name', sa.String(length=100), nullable=False),
        sa.Column('source_url', sa.String(length=2000), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name'),
    )

    op.create_table(
        'darkweb_onion_targets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_name', sa.String(length=100), nullable=False),
        sa.Column('source_repo', sa.String(length=300), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('group_name', sa.String(length=300), nullable=True),
        sa.Column('onion_url', sa.String(length=2000), nullable=False),
        sa.Column('normalized_onion_url', sa.String(length=2000), nullable=False),
        sa.Column('clearweb_reference', sa.String(length=2000), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_scanned_at', sa.DateTime(), nullable=True),
        sa.Column('last_http_status', sa.Integer(), nullable=True),
        sa.Column('last_latency_ms', sa.Integer(), nullable=True),
        sa.Column('last_title', sa.String(length=500), nullable=True),
        sa.Column('last_snippet', sa.Text(), nullable=True),
        sa.Column('last_content_hash', sa.String(length=64), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('normalized_onion_url'),
    )
    op.create_index('idx_onion_target_source', 'darkweb_onion_targets', ['source_name'], unique=False)
    op.create_index('idx_onion_target_category', 'darkweb_onion_targets', ['category'], unique=False)
    op.create_index('idx_onion_target_status', 'darkweb_onion_targets', ['status'], unique=False)
    op.create_index('idx_onion_target_hash', 'darkweb_onion_targets', ['last_content_hash'], unique=False)

    op.create_table(
        'darkweb_target_scan_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('scan_id', sa.UUID(), nullable=True),
        sa.Column('onion_url', sa.String(length=2000), nullable=False),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('snippet', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('detected_onion_links', sa.JSON(), nullable=True),
        sa.Column('emails', sa.JSON(), nullable=True),
        sa.Column('crypto_wallets', sa.JSON(), nullable=True),
        sa.Column('error_reason', sa.Text(), nullable=True),
        sa.Column('scanned_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_target_scan_target', 'darkweb_target_scan_results', ['target_id'], unique=False)
    op.create_index('idx_target_scan_hash', 'darkweb_target_scan_results', ['content_hash'], unique=False)
    op.create_index('idx_target_scan_scanned', 'darkweb_target_scan_results', ['scanned_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_target_scan_scanned', table_name='darkweb_target_scan_results')
    op.drop_index('idx_target_scan_hash', table_name='darkweb_target_scan_results')
    op.drop_index('idx_target_scan_target', table_name='darkweb_target_scan_results')
    op.drop_table('darkweb_target_scan_results')
    op.drop_index('idx_onion_target_hash', table_name='darkweb_onion_targets')
    op.drop_index('idx_onion_target_status', table_name='darkweb_onion_targets')
    op.drop_index('idx_onion_target_category', table_name='darkweb_onion_targets')
    op.drop_index('idx_onion_target_source', table_name='darkweb_onion_targets')
    op.drop_table('darkweb_onion_targets')
    op.drop_table('darkweb_feed_cache')
    op.drop_index('idx_mention_triage_status', table_name='darkweb_mentions')
    op.drop_index('idx_mention_content_hash', table_name='darkweb_mentions')
    op.drop_index('idx_mention_dedup_hash', table_name='darkweb_mentions')
    op.drop_index('idx_mention_source_url', table_name='darkweb_mentions')
    op.drop_column('darkweb_mentions', 'triage_status')
    op.drop_column('darkweb_mentions', 'severity_reason')
    op.drop_column('darkweb_mentions', 'content_hash')
    op.drop_column('darkweb_mentions', 'dedup_hash')
    op.drop_column('darkweb_mentions', 'normalized_source_url')
    op.drop_column('darkweb_mentions', 'effective_query')
    op.drop_column('darkweb_mentions', 'original_query')
