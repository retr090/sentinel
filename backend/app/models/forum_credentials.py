import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean,
    DateTime, JSON, Text, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class ForumCredential(Base):
    __tablename__ = "forum_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forum_id = Column(String(100), nullable=False, unique=True)
    forum_name = Column(String(200), nullable=False)
    forum_url = Column(String(500), nullable=False)
    username = Column(String(200), nullable=True)

    # Fernet-encrypted password — never store plaintext
    encrypted_password = Column(Text, nullable=True)

    login_url = Column(String(500), nullable=True)
    login_form_data = Column(JSON, default=dict)

    # mybb / phpbb / xenforo / custom
    forum_software = Column(String(50), nullable=True, default="mybb")

    search_url_pattern = Column(String(500), nullable=True)
    result_selector = Column(String(200), nullable=True)

    session_cookies = Column(JSON, default=dict)
    auto_login = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    login_attempts = Column(Integer, default=0)
    last_login_attempt = Column(DateTime, nullable=True)
    last_successful_login = Column(DateTime, nullable=True)
    session_valid_until = Column(DateTime, nullable=True)
    last_used = Column(DateTime, nullable=True)

    added_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_forum_cred_forum_id", "forum_id"),
        Index("idx_forum_cred_active", "is_active"),
    )
