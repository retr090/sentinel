from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(512), nullable=False, index=True)
    profile_type = Column(String(64), nullable=False, index=True)  # person, org, domain, ip, email
    query_value = Column(String(512), nullable=False, index=True)
    risk_score = Column(Float, default=0.0)
    summary = Column(Text)
    analyst_notes = Column(Text)
    raw_data = Column(JSON, default=dict)
    is_archived = Column(Boolean, default=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProfileAttribute(Base):
    __tablename__ = "profile_attributes"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    attr_type = Column(String(64), nullable=False)  # email, phone, ip, domain, whois, dns, cert, etc.
    attr_key = Column(String(256))
    attr_value = Column(Text)
    source = Column(String(128))
    confidence = Column(Float, default=0.5)
    raw_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProfileLink(Base):
    __tablename__ = "profile_links"

    id = Column(Integer, primary_key=True, index=True)
    source_profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    target_profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    link_type = Column(String(64))  # owns, associated_with, resolves_to, registered_by
    confidence = Column(Float, default=0.5)
    source = Column(String(128))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProfileNote(Base):
    __tablename__ = "profile_notes"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
