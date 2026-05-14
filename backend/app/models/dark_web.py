from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class WatchlistKeyword(Base):
    __tablename__ = "watchlist_keywords"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(256), nullable=False, unique=True, index=True)
    category = Column(String(64))  # domain, person, org, general
    severity = Column(String(32), default="MEDIUM")
    is_active = Column(Boolean, default=True)
    last_scanned = Column(DateTime(timezone=True))
    scan_interval_hours = Column(Integer, default=6)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DarkWebMention(Base):
    __tablename__ = "dark_web_mentions"

    id = Column(Integer, primary_key=True, index=True)
    keyword_id = Column(Integer, ForeignKey("watchlist_keywords.id", ondelete="SET NULL"), nullable=True, index=True)
    keyword = Column(String(256), nullable=False)
    source = Column(String(128))  # ahmia, paste, intelx
    source_url = Column(String(1024))
    title = Column(String(512))
    snippet = Column(Text)
    severity = Column(String(32), default="MEDIUM")
    analyst_notes = Column(Text)
    is_archived = Column(Boolean, default=False)
    is_acknowledged = Column(Boolean, default=False)
    found_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BreachResult(Base):
    __tablename__ = "breach_results"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(256), nullable=False, index=True)
    query_type = Column(String(32))  # email, domain
    breach_name = Column(String(256))
    breach_date = Column(String(64))
    data_classes = Column(JSON, default=list)
    is_verified = Column(Boolean, default=False)
    raw_data = Column(JSON, default=dict)
    is_archived = Column(Boolean, default=False)
    found_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PasteHit(Base):
    __tablename__ = "paste_hits"

    id = Column(Integer, primary_key=True, index=True)
    keyword_id = Column(Integer, ForeignKey("watchlist_keywords.id", ondelete="SET NULL"), nullable=True)
    keyword = Column(String(256))
    paste_site = Column(String(64))  # pastebin, ghostbin, rentry
    paste_url = Column(String(1024))
    paste_title = Column(String(512))
    snippet = Column(Text)
    is_archived = Column(Boolean, default=False)
    found_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
