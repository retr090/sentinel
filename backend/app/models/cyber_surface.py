from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class MonitoredAsset(Base):
    __tablename__ = "monitored_assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False)
    asset_type = Column(String(32), nullable=False, index=True)  # domain, ip, ip_range
    value = Column(String(512), nullable=False, unique=True, index=True)
    organization = Column(String(256))
    tags = Column(JSON, default=list)
    risk_grade = Column(String(8))  # A, B, C, D, F
    risk_score = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    last_scanned = Column(DateTime(timezone=True))
    scan_interval_hours = Column(Integer, default=24)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AssetScan(Base):
    __tablename__ = "asset_scans"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("monitored_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_type = Column(String(64))  # ssl, ports, headers, dns, subdomains
    status = Column(String(32), default="pending")  # pending, running, complete, failed
    results = Column(JSON, default=dict)
    changes_detected = Column(Boolean, default=False)
    change_summary = Column(Text)
    risk_score = Column(Float)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class AssetVulnerability(Base):
    __tablename__ = "asset_vulnerabilities"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("monitored_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id = Column(Integer, ForeignKey("asset_scans.id", ondelete="SET NULL"), nullable=True)
    cve_id = Column(String(32), index=True)
    title = Column(String(512))
    description = Column(Text)
    severity = Column(String(32))  # CRITICAL, HIGH, MEDIUM, LOW
    cvss_score = Column(Float)
    service = Column(String(128))
    port = Column(Integer)
    is_resolved = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    discovered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AssetAlert(Base):
    __tablename__ = "asset_alerts"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("monitored_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id = Column(Integer, ForeignKey("asset_scans.id", ondelete="SET NULL"), nullable=True)
    alert_type = Column(String(64))  # ssl_expiry, new_port, service_change, vuln_found
    title = Column(String(512))
    description = Column(Text)
    severity = Column(String(32), default="MEDIUM")
    is_acknowledged = Column(Boolean, default=False)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
