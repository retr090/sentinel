import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text, Float, Index
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class DarkWebMention(Base):
    __tablename__ = "darkweb_mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword_id = Column(UUID(as_uuid=True), nullable=True)
    keyword_matched = Column(String(500), nullable=False)
    original_query = Column(String(500), nullable=True)
    effective_query = Column(String(700), nullable=True)
    source = Column(String(100), nullable=False)
    source_url = Column(String(2000), nullable=True)
    normalized_source_url = Column(String(2000), nullable=True)
    dedup_hash = Column(String(64), nullable=True)
    content_hash = Column(String(64), nullable=True)
    title = Column(String(1000), nullable=True)
    snippet = Column(Text, nullable=True)
    full_content = Column(Text, nullable=True)
    severity = Column(String(20), default="MEDIUM")
    severity_reason = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    threat_actor = Column(String(200), nullable=True)
    victim_org = Column(String(500), nullable=True)
    victim_country = Column(String(10), nullable=True)
    is_reviewed = Column(Boolean, default=False)
    is_false_positive = Column(Boolean, default=False)
    triage_status = Column(String(30), default="new")
    analyst_notes = Column(Text, nullable=True)
    analyst_seen_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    feed_posted_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    raw_data = Column(JSON, default=dict)

    __table_args__ = (
        Index('idx_mention_source', 'source'),
        Index('idx_mention_severity', 'severity'),
        Index('idx_mention_discovered', 'discovered_at'),
        Index('idx_mention_keyword', 'keyword_matched'),
        Index('idx_mention_reviewed', 'is_reviewed'),
        Index('idx_mention_source_url', 'normalized_source_url'),
        Index('idx_mention_dedup_hash', 'dedup_hash'),
        Index('idx_mention_content_hash', 'content_hash'),
        Index('idx_mention_triage_status', 'triage_status'),
    )


class DarkWebScan(Base):
    __tablename__ = "darkweb_scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_type = Column(String(100), nullable=False)
    source = Column(String(100), nullable=True)
    status = Column(String(20), default="pending")
    keywords_scanned = Column(Integer, default=0)
    mentions_found = Column(Integer, default=0)
    new_mentions = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_scan_status', 'status'),
        Index('idx_scan_created', 'created_at'),
    )


class DarkWebAlert(Base):
    __tablename__ = "darkweb_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mention_id = Column(UUID(as_uuid=True), nullable=False)
    keyword_id = Column(UUID(as_uuid=True), nullable=True)
    severity = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    notification_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
