from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class GeoItem(Base):
    __tablename__ = "geo_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False)
    description = Column(Text)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    item_type = Column(String(64), index=True)  # threat, news, ship, flight, incident
    module_source = Column(String(64))  # which module created this
    source_id = Column(Integer)  # id in source module table
    severity = Column(String(32), default="INFO")
    metadata_ = Column("metadata", JSON, default=dict)
    is_archived = Column(Boolean, default=False)
    event_time = Column(DateTime(timezone=True), index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AreaOfInterest(Base):
    __tablename__ = "areas_of_interest"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text)
    geojson = Column(JSON, nullable=False)  # GeoJSON polygon
    alert_on_match = Column(Boolean, default=True)
    item_types = Column(JSON, default=list)  # which item types to alert on
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GeoAlert(Base):
    __tablename__ = "geo_alerts"

    id = Column(Integer, primary_key=True, index=True)
    aoi_id = Column(Integer, ForeignKey("areas_of_interest.id", ondelete="CASCADE"), nullable=False, index=True)
    geo_item_id = Column(Integer, ForeignKey("geo_items.id", ondelete="CASCADE"), nullable=False)
    severity = Column(String(32), default="MEDIUM")
    is_acknowledged = Column(Boolean, default=False)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
