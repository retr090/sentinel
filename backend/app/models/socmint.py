from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, BigInteger
from sqlalchemy.sql import func
from app.core.database import Base


class SocialKeyword(Base):
    __tablename__ = "social_keywords"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(256), nullable=False, unique=True)
    platforms = Column(JSON, default=list)  # twitter, reddit, youtube, telegram
    is_active = Column(Boolean, default=True)
    alert_on_spike = Column(Boolean, default=True)
    spike_threshold = Column(Integer, default=50)
    last_scanned = Column(DateTime(timezone=True))
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(32), nullable=False, index=True)  # twitter, reddit, youtube, telegram
    platform_post_id = Column(String(256), index=True)
    keyword_matched = Column(String(256), index=True)
    account_id = Column(Integer, ForeignKey("social_accounts.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text)
    url = Column(String(2048))
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    sentiment_score = Column(Float)
    sentiment_label = Column(String(16))
    geo_tag = Column(String(256))
    raw_data = Column(JSON, default=dict)
    is_archived = Column(Boolean, default=False)
    posted_at = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(32), nullable=False)
    platform_user_id = Column(String(256))
    username = Column(String(256), index=True)
    display_name = Column(String(512))
    followers = Column(BigInteger, default=0)
    bio = Column(Text)
    is_verified = Column(Boolean, default=False)
    risk_score = Column(Float, default=0.0)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SocialAlert(Base):
    __tablename__ = "social_alerts"

    id = Column(Integer, primary_key=True, index=True)
    keyword_id = Column(Integer, ForeignKey("social_keywords.id", ondelete="SET NULL"), nullable=True)
    keyword = Column(String(256))
    platform = Column(String(32))
    mention_count = Column(Integer, default=0)
    window_hours = Column(Integer, default=1)
    severity = Column(String(32), default="MEDIUM")
    is_acknowledged = Column(Boolean, default=False)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
