from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False)
    description = Column(Text)
    severity = Column(String(32), nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    module = Column(String(64), nullable=False, index=True)  # which module generated this
    source_type = Column(String(64))
    source_id = Column(Integer)
    metadata_ = Column("metadata", JSON, default=dict)
    status = Column(String(32), default="open", index=True)  # open, acknowledged, resolved, false_positive
    is_archived = Column(Boolean, default=False)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AlertAssignment(Base):
    __tablename__ = "alert_assignments"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False)
    report_type = Column(String(64))  # sitrep, incident, threat_assessment, custom
    template_id = Column(Integer, ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True)
    modules = Column(JSON, default=list)
    date_from = Column(DateTime(timezone=True))
    date_to = Column(DateTime(timezone=True))
    parameters = Column(JSON, default=dict)
    file_path = Column(String(1024))
    status = Column(String(32), default="pending")  # pending, generating, ready, failed
    error_message = Column(Text)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    generated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False, unique=True)
    report_type = Column(String(64))
    description = Column(Text)
    template_html = Column(Text)
    default_modules = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NotificationConfig(Base):
    __tablename__ = "notification_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False)
    channel_type = Column(String(32), nullable=False)  # email, telegram, webhook
    config = Column(JSON, nullable=False)  # channel-specific config
    min_severity = Column(String(32), default="HIGH")
    modules = Column(JSON, default=list)  # empty = all modules
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
