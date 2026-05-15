from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime


class IOCCreate(BaseModel):
    value: str
    ioc_type: str
    analyst_notes: Optional[str] = None
    tags: Optional[List[str]] = []


class IOCOut(BaseModel):
    id: int
    value: str
    ioc_type: str
    risk_score: float
    risk_level: Optional[str] = "clean"
    sources: List[str]
    raw_data: Dict[str, Any]
    tags: Optional[List[str]] = []
    analyst_notes: Optional[str]
    is_archived: bool = False
    first_seen: datetime
    last_seen: datetime
    created_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class IOCLookupRequest(BaseModel):
    value: str


class IOCLookupOut(BaseModel):
    ioc: IOCOut
    enrichments: Dict[str, Any]
    risk_score: float
    risk_level: str
    analysis: Optional[Dict[str, Any]] = None


class IOCNotesUpdate(BaseModel):
    notes: str


class IOCBulkLookupRequest(BaseModel):
    iocs: List[str]


class IOCBulkJobOut(BaseModel):
    id: int
    status: str
    total: int
    processed: int
    results: Optional[List[Any]] = []
    created_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class IOCSearchResult(BaseModel):
    ioc: IOCOut
    enrichments: Dict[str, Any]


class FeedItemOut(BaseModel):
    id: int
    feed_id: int
    title: Optional[str]
    description: Optional[str]
    ioc_value: Optional[str]
    ioc_type: Optional[str]
    severity: Optional[str]
    source_url: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ThreatFeedOut(BaseModel):
    id: int
    name: str
    feed_type: str
    is_active: bool
    last_fetched: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class IOCBulkImport(BaseModel):
    iocs: List[str]
    ioc_type: str
    tags: Optional[List[str]] = []


class ExportBulkRequest(BaseModel):
    ids: List[int]
