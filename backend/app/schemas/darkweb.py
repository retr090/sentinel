from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from uuid import UUID


class KeywordCreate(BaseModel):
    keyword: str = Field(..., min_length=2, max_length=500)
    aliases: List[str] = []
    category: str = "General"
    priority: str = "MEDIUM"
    alert_mode: str = "immediate"
    sources: List[str] = [
        "ransomware_live", "ahmia", "darksearch", "pastebin", "rss_feeds"
    ]
    notes: Optional[str] = None


class KeywordUpdate(BaseModel):
    keyword: Optional[str] = None
    aliases: Optional[List[str]] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    alert_mode: Optional[str] = None
    sources: Optional[List[str]] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class KeywordResponse(BaseModel):
    id: UUID
    keyword: str
    aliases: List[str]
    category: str
    priority: str
    alert_mode: str
    sources: List[str]
    is_active: bool
    hit_count: int
    last_hit: Optional[datetime]
    created_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True


class MentionResponse(BaseModel):
    id: UUID
    keyword_matched: str
    source: str
    source_url: Optional[str]
    title: Optional[str]
    snippet: Optional[str]
    severity: str
    category: Optional[str]
    threat_actor: Optional[str]
    victim_org: Optional[str]
    victim_country: Optional[str]
    is_reviewed: bool
    is_false_positive: bool
    analyst_notes: Optional[str]
    discovered_at: datetime
    published_at: Optional[datetime]

    class Config:
        from_attributes = True


class MentionUpdate(BaseModel):
    is_reviewed: Optional[bool] = None
    is_false_positive: Optional[bool] = None
    analyst_notes: Optional[str] = None


class ScanResponse(BaseModel):
    id: UUID
    scan_type: str
    source: Optional[str]
    status: str
    keywords_scanned: int
    mentions_found: int
    new_mentions: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class DarkWebStats(BaseModel):
    total_keywords: int
    active_keywords: int
    total_mentions: int
    unreviewed_mentions: int
    critical_mentions: int
    high_mentions: int
    mentions_24h: int
    mentions_7d: int
    last_scan: Optional[datetime]
    sources_status: dict


class BulkKeywordImport(BaseModel):
    keywords: List[KeywordCreate]


class ManualSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    sources: List[str] = ["ahmia", "darksearch", "pastebin"]
