from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class IOC(Base):
    __tablename__ = "iocs"

    id = Column(Integer, primary_key=True, index=True)
    value = Column(String(512), nullable=False, index=True)
    ioc_type = Column(String(32), nullable=False, index=True)  # ip, domain, hash, url, email
    risk_score = Column(Float, default=0.0)
    sources = Column(JSON, default=list)
    raw_data = Column(JSON, default=dict)
    is_archived = Column(Boolean, default=False)
    analyst_notes = Column(Text)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IOCTag(Base):
    __tablename__ = "ioc_tags"

    id = Column(Integer, primary_key=True, index=True)
    ioc_id = Column(Integer, ForeignKey("iocs.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String(64), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ThreatFeed(Base):
    __tablename__ = "threat_feeds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True)
    source_url = Column(String(512))
    feed_type = Column(String(64))  # alienvault, abusech, circl, etc.
    is_active = Column(Boolean, default=True)
    last_fetched = Column(DateTime(timezone=True))
    fetch_interval_seconds = Column(Integer, default=3600)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FeedItem(Base):
    __tablename__ = "feed_items"

    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, ForeignKey("threat_feeds.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(512))
    description = Column(Text)
    ioc_value = Column(String(512), index=True)
    ioc_type = Column(String(32))
    severity = Column(String(32))
    raw_data = Column(JSON, default=dict)
    source_url = Column(String(512))
    published_at = Column(DateTime(timezone=True))
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
