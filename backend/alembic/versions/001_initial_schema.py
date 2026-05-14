"""Initial schema - all modules

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users & Audit
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(64), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('role', sa.String(32), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer()),
        sa.Column('username', sa.String(64)),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('resource_type', sa.String(64)),
        sa.Column('resource_id', sa.String(64)),
        sa.Column('details', sa.Text()),
        sa.Column('ip_address', sa.String(64)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])

    # Threat Intel
    op.create_table('threat_feeds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('source_url', sa.String(512)),
        sa.Column('feed_type', sa.String(64)),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_fetched', sa.DateTime(timezone=True)),
        sa.Column('fetch_interval_seconds', sa.Integer(), server_default='3600'),
        sa.Column('config', JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table('iocs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('value', sa.String(512), nullable=False),
        sa.Column('ioc_type', sa.String(32), nullable=False),
        sa.Column('risk_score', sa.Float(), server_default='0'),
        sa.Column('sources', JSON),
        sa.Column('raw_data', JSON),
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
        sa.Column('analyst_notes', sa.Text()),
        sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_iocs_value', 'iocs', ['value'])
    op.create_index('ix_iocs_ioc_type', 'iocs', ['ioc_type'])

    op.create_table('ioc_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ioc_id', sa.Integer(), sa.ForeignKey('iocs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tag', sa.String(64), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ioc_tags_ioc_id', 'ioc_tags', ['ioc_id'])

    op.create_table('feed_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('feed_id', sa.Integer(), sa.ForeignKey('threat_feeds.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(512)),
        sa.Column('description', sa.Text()),
        sa.Column('ioc_value', sa.String(512)),
        sa.Column('ioc_type', sa.String(32)),
        sa.Column('severity', sa.String(32)),
        sa.Column('raw_data', JSON),
        sa.Column('source_url', sa.String(512)),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_feed_items_feed_id', 'feed_items', ['feed_id'])
    op.create_index('ix_feed_items_created_at', 'feed_items', ['created_at'])

    # Dark Web
    op.create_table('watchlist_keywords',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(256), nullable=False),
        sa.Column('category', sa.String(64)),
        sa.Column('severity', sa.String(32), server_default='MEDIUM'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_scanned', sa.DateTime(timezone=True)),
        sa.Column('scan_interval_hours', sa.Integer(), server_default='6'),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('keyword'),
    )

    op.create_table('dark_web_mentions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword_id', sa.Integer(), sa.ForeignKey('watchlist_keywords.id', ondelete='SET NULL')),
        sa.Column('keyword', sa.String(256), nullable=False),
        sa.Column('source', sa.String(128)),
        sa.Column('source_url', sa.String(1024)),
        sa.Column('title', sa.String(512)),
        sa.Column('snippet', sa.Text()),
        sa.Column('severity', sa.String(32), server_default='MEDIUM'),
        sa.Column('analyst_notes', sa.Text()),
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
        sa.Column('is_acknowledged', sa.Boolean(), server_default='false'),
        sa.Column('found_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dark_web_mentions_found_at', 'dark_web_mentions', ['found_at'])
    op.create_index('ix_dark_web_mentions_keyword_id', 'dark_web_mentions', ['keyword_id'])

    op.create_table('breach_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query', sa.String(256), nullable=False),
        sa.Column('query_type', sa.String(32)),
        sa.Column('breach_name', sa.String(256)),
        sa.Column('breach_date', sa.String(64)),
        sa.Column('data_classes', JSON),
        sa.Column('is_verified', sa.Boolean(), server_default='false'),
        sa.Column('raw_data', JSON),
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
        sa.Column('found_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_breach_results_query', 'breach_results', ['query'])

    op.create_table('paste_hits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword_id', sa.Integer(), sa.ForeignKey('watchlist_keywords.id', ondelete='SET NULL')),
        sa.Column('keyword', sa.String(256)),
        sa.Column('paste_site', sa.String(64)),
        sa.Column('paste_url', sa.String(1024)),
        sa.Column('paste_title', sa.String(512)),
        sa.Column('snippet', sa.Text()),
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
        sa.Column('found_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_paste_hits_found_at', 'paste_hits', ['found_at'])

    # News
    op.create_table('news_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('url', sa.String(1024), nullable=False),
        sa.Column('source_type', sa.String(32)),
        sa.Column('category', sa.String(64)),
        sa.Column('language', sa.String(8), server_default='en'),
        sa.Column('credibility_score', sa.Float(), server_default='0.5'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_fetched', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url'),
    )

    op.create_table('news_articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('news_sources.id', ondelete='SET NULL')),
        sa.Column('title', sa.String(1024), nullable=False),
        sa.Column('url', sa.String(2048)),
        sa.Column('content_snippet', sa.Text()),
        sa.Column('author', sa.String(256)),
        sa.Column('category', sa.String(64)),
        sa.Column('sentiment_score', sa.Float()),
        sa.Column('sentiment_label', sa.String(16)),
        sa.Column('keywords_matched', JSON),
        sa.Column('language', sa.String(8), server_default='en'),
        sa.Column('geo_tags', JSON),
        sa.Column('raw_data', JSON),
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url'),
    )
    op.create_index('ix_news_articles_published_at', 'news_articles', ['published_at'])
    op.create_index('ix_news_articles_category', 'news_articles', ['category'])

    op.create_table('news_keywords',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(256), nullable=False),
        sa.Column('category', sa.String(64)),
        sa.Column('alert_threshold', sa.Integer(), server_default='10'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('keyword'),
    )

    op.create_table('news_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword_id', sa.Integer(), sa.ForeignKey('news_keywords.id', ondelete='SET NULL')),
        sa.Column('keyword', sa.String(256)),
        sa.Column('mention_count', sa.Integer(), server_default='0'),
        sa.Column('window_hours', sa.Integer(), server_default='1'),
        sa.Column('severity', sa.String(32), server_default='MEDIUM'),
        sa.Column('is_acknowledged', sa.Boolean(), server_default='false'),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_news_alerts_triggered_at', 'news_alerts', ['triggered_at'])

    # GEOINT
    op.create_table('geo_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('item_type', sa.String(64)),
        sa.Column('module_source', sa.String(64)),
        sa.Column('source_id', sa.Integer()),
        sa.Column('severity', sa.String(32), server_default='INFO'),
        sa.Column('metadata', JSON),
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
        sa.Column('event_time', sa.DateTime(timezone=True)),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_geo_items_item_type', 'geo_items', ['item_type'])
    op.create_index('ix_geo_items_event_time', 'geo_items', ['event_time'])

    op.create_table('areas_of_interest',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('geojson', JSON, nullable=False),
        sa.Column('alert_on_match', sa.Boolean(), server_default='true'),
        sa.Column('item_types', JSON),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('geo_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('aoi_id', sa.Integer(), sa.ForeignKey('areas_of_interest.id', ondelete='CASCADE'), nullable=False),
        sa.Column('geo_item_id', sa.Integer(), sa.ForeignKey('geo_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('severity', sa.String(32), server_default='MEDIUM'),
        sa.Column('is_acknowledged', sa.Boolean(), server_default='false'),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_geo_alerts_triggered_at', 'geo_alerts', ['triggered_at'])
    op.create_index('ix_geo_alerts_aoi_id', 'geo_alerts', ['aoi_id'])

    # Profiles
    op.create_table('profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(512), nullable=False),
        sa.Column('profile_type', sa.String(64), nullable=False),
        sa.Column('query_value', sa.String(512), nullable=False),
        sa.Column('risk_score', sa.Float(), server_default='0'),
        sa.Column('summary', sa.Text()),
        sa.Column('analyst_notes', sa.Text()),
        sa.Column('raw_data', JSON),
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_profiles_name', 'profiles', ['name'])
    op.create_index('ix_profiles_profile_type', 'profiles', ['profile_type'])
    op.create_index('ix_profiles_query_value', 'profiles', ['query_value'])

    op.create_table('profile_attributes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attr_type', sa.String(64), nullable=False),
        sa.Column('attr_key', sa.String(256)),
        sa.Column('attr_value', sa.Text()),
        sa.Column('source', sa.String(128)),
        sa.Column('confidence', sa.Float(), server_default='0.5'),
        sa.Column('raw_data', JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_profile_attributes_profile_id', 'profile_attributes', ['profile_id'])

    op.create_table('profile_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_profile_id', sa.Integer(), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_profile_id', sa.Integer(), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('link_type', sa.String(64)),
        sa.Column('confidence', sa.Float(), server_default='0.5'),
        sa.Column('source', sa.String(128)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_profile_links_source_profile_id', 'profile_links', ['source_profile_id'])
    op.create_index('ix_profile_links_target_profile_id', 'profile_links', ['target_profile_id'])

    op.create_table('profile_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_profile_notes_profile_id', 'profile_notes', ['profile_id'])

    # SOCMINT
    op.create_table('social_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(32), nullable=False),
        sa.Column('platform_user_id', sa.String(256)),
        sa.Column('username', sa.String(256)),
        sa.Column('display_name', sa.String(512)),
        sa.Column('followers', sa.BigInteger(), server_default='0'),
        sa.Column('bio', sa.Text()),
        sa.Column('is_verified', sa.Boolean(), server_default='false'),
        sa.Column('risk_score', sa.Float(), server_default='0'),
        sa.Column('metadata', JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_social_accounts_username', 'social_accounts', ['username'])

    op.create_table('social_keywords',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(256), nullable=False),
        sa.Column('platforms', JSON),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('alert_on_spike', sa.Boolean(), server_default='true'),
        sa.Column('spike_threshold', sa.Integer(), server_default='50'),
        sa.Column('last_scanned', sa.DateTime(timezone=True)),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('keyword'),
    )

    op.create_table('social_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(32), nullable=False),
        sa.Column('platform_post_id', sa.String(256)),
        sa.Column('keyword_matched', sa.String(256)),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('social_accounts.id', ondelete='SET NULL')),
        sa.Column('content', sa.Text()),
        sa.Column('url', sa.String(2048)),
        sa.Column('likes', sa.Integer(), server_default='0'),
        sa.Column('shares', sa.Integer(), server_default='0'),
        sa.Column('comments', sa.Integer(), server_default='0'),
        sa.Column('sentiment_score', sa.Float()),
        sa.Column('sentiment_label', sa.String(16)),
        sa.Column('geo_tag', sa.String(256)),
        sa.Column('raw_data', JSON),
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
        sa.Column('posted_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_social_posts_platform', 'social_posts', ['platform'])
    op.create_index('ix_social_posts_posted_at', 'social_posts', ['posted_at'])

    op.create_table('social_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword_id', sa.Integer(), sa.ForeignKey('social_keywords.id', ondelete='SET NULL')),
        sa.Column('keyword', sa.String(256)),
        sa.Column('platform', sa.String(32)),
        sa.Column('mention_count', sa.Integer(), server_default='0'),
        sa.Column('window_hours', sa.Integer(), server_default='1'),
        sa.Column('severity', sa.String(32), server_default='MEDIUM'),
        sa.Column('is_acknowledged', sa.Boolean(), server_default='false'),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_social_alerts_triggered_at', 'social_alerts', ['triggered_at'])

    # Cyber Surface
    op.create_table('monitored_assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('asset_type', sa.String(32), nullable=False),
        sa.Column('value', sa.String(512), nullable=False),
        sa.Column('organization', sa.String(256)),
        sa.Column('tags', JSON),
        sa.Column('risk_grade', sa.String(8)),
        sa.Column('risk_score', sa.Float(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_scanned', sa.DateTime(timezone=True)),
        sa.Column('scan_interval_hours', sa.Integer(), server_default='24'),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('value'),
    )
    op.create_index('ix_monitored_assets_asset_type', 'monitored_assets', ['asset_type'])

    op.create_table('asset_scans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('monitored_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scan_type', sa.String(64)),
        sa.Column('status', sa.String(32), server_default='pending'),
        sa.Column('results', JSON),
        sa.Column('changes_detected', sa.Boolean(), server_default='false'),
        sa.Column('change_summary', sa.Text()),
        sa.Column('risk_score', sa.Float()),
        sa.Column('error_message', sa.Text()),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_asset_scans_asset_id', 'asset_scans', ['asset_id'])
    op.create_index('ix_asset_scans_created_at', 'asset_scans', ['created_at'])

    op.create_table('asset_vulnerabilities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('monitored_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scan_id', sa.Integer(), sa.ForeignKey('asset_scans.id', ondelete='SET NULL')),
        sa.Column('cve_id', sa.String(32)),
        sa.Column('title', sa.String(512)),
        sa.Column('description', sa.Text()),
        sa.Column('severity', sa.String(32)),
        sa.Column('cvss_score', sa.Float()),
        sa.Column('service', sa.String(128)),
        sa.Column('port', sa.Integer()),
        sa.Column('is_resolved', sa.Boolean(), server_default='false'),
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
        sa.Column('discovered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_asset_vulnerabilities_asset_id', 'asset_vulnerabilities', ['asset_id'])
    op.create_index('ix_asset_vulnerabilities_cve_id', 'asset_vulnerabilities', ['cve_id'])
    op.create_index('ix_asset_vulnerabilities_discovered_at', 'asset_vulnerabilities', ['discovered_at'])

    op.create_table('asset_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('monitored_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scan_id', sa.Integer(), sa.ForeignKey('asset_scans.id', ondelete='SET NULL')),
        sa.Column('alert_type', sa.String(64)),
        sa.Column('title', sa.String(512)),
        sa.Column('description', sa.Text()),
        sa.Column('severity', sa.String(32), server_default='MEDIUM'),
        sa.Column('is_acknowledged', sa.Boolean(), server_default='false'),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_asset_alerts_asset_id', 'asset_alerts', ['asset_id'])
    op.create_index('ix_asset_alerts_triggered_at', 'asset_alerts', ['triggered_at'])

    # Alerts & Reports
    op.create_table('report_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('report_type', sa.String(64)),
        sa.Column('description', sa.Text()),
        sa.Column('template_html', sa.Text()),
        sa.Column('default_modules', JSON),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table('notification_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('channel_type', sa.String(32), nullable=False),
        sa.Column('config', JSON, nullable=False),
        sa.Column('min_severity', sa.String(32), server_default='HIGH'),
        sa.Column('modules', JSON),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('severity', sa.String(32), nullable=False),
        sa.Column('module', sa.String(64), nullable=False),
        sa.Column('source_type', sa.String(64)),
        sa.Column('source_id', sa.Integer()),
        sa.Column('metadata', JSON),
        sa.Column('status', sa.String(32), server_default='open'),
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alerts_severity', 'alerts', ['severity'])
    op.create_index('ix_alerts_module', 'alerts', ['module'])
    op.create_index('ix_alerts_status', 'alerts', ['status'])
    op.create_index('ix_alerts_triggered_at', 'alerts', ['triggered_at'])

    op.create_table('alert_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), sa.ForeignKey('alerts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_to', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('assigned_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alert_assignments_alert_id', 'alert_assignments', ['alert_id'])

    op.create_table('reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('report_type', sa.String(64)),
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('report_templates.id', ondelete='SET NULL')),
        sa.Column('modules', JSON),
        sa.Column('date_from', sa.DateTime(timezone=True)),
        sa.Column('date_to', sa.DateTime(timezone=True)),
        sa.Column('parameters', JSON),
        sa.Column('file_path', sa.String(1024)),
        sa.Column('status', sa.String(32), server_default='pending'),
        sa.Column('error_message', sa.Text()),
        sa.Column('generated_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('generated_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    for table in [
        'reports', 'alert_assignments', 'alerts', 'notification_configs', 'report_templates',
        'asset_alerts', 'asset_vulnerabilities', 'asset_scans', 'monitored_assets',
        'social_alerts', 'social_posts', 'social_keywords', 'social_accounts',
        'profile_notes', 'profile_links', 'profile_attributes', 'profiles',
        'geo_alerts', 'areas_of_interest', 'geo_items',
        'news_alerts', 'news_keywords', 'news_articles', 'news_sources',
        'paste_hits', 'breach_results', 'dark_web_mentions', 'watchlist_keywords',
        'feed_items', 'ioc_tags', 'iocs', 'threat_feeds',
        'audit_logs', 'users',
    ]:
        op.drop_table(table)
