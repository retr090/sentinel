from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class NewsSource(Base):
    __tablename__ = "news_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False)
    url = Column(String(1024), nullable=False, unique=True)
    source_type = Column(String(32))  # rss, newsapi, gdelt, mediastack
    category = Column(String(64))  # military, cyber, politics, regional
    language = Column(String(8), default="en")
    credibility_score = Column(Float, default=0.5)
    is_active = Column(Boolean, default=True)
    last_fetched = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("news_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(1024), nullable=False)
    url = Column(String(2048), unique=True)
    content_snippet = Column(Text)
    author = Column(String(256))
    category = Column(String(64), index=True)
    sentiment_score = Column(Float)  # -1 to 1
    sentiment_label = Column(String(16))  # positive, negative, neutral
    keywords_matched = Column(JSON, default=list)
    language = Column(String(8), default="en")
    geo_tags = Column(JSON, default=list)
    raw_data = Column(JSON, default=dict)
    is_archived = Column(Boolean, default=False)
    published_at = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NewsKeyword(Base):
    __tablename__ = "news_keywords"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(256), nullable=False, unique=True)
    category = Column(String(64))
    alert_threshold = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NewsAlert(Base):
    __tablename__ = "news_alerts"

    id = Column(Integer, primary_key=True, index=True)
    keyword_id = Column(Integer, ForeignKey("news_keywords.id", ondelete="SET NULL"), nullable=True)
    keyword = Column(String(256))
    mention_count = Column(Integer, default=0)
    window_hours = Column(Integer, default=1)
    severity = Column(String(32), default="MEDIUM")
    is_acknowledged = Column(Boolean, default=False)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
