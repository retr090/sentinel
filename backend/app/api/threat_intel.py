from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.core.security import get_current_user, require_analyst
from app.models.user import User
from app.models.threat_intel import IOC, IOCTag, ThreatFeed, FeedItem
from app.schemas.threat_intel import IOCCreate, IOCOut, FeedItemOut, ThreatFeedOut, IOCBulkImport
from app.schemas.common import PaginatedResponse
from app.services.threat_intel import (
    enrich_ip, enrich_domain, enrich_hash, enrich_url,
    enrich_email, enrich_cve, enrich_asn, calculate_risk_score
)
import math
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/threat-intel", tags=["threat-intel"])


def detect_ioc_type(value: str) -> str:
    import re
    ip_re = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    hash_re = re.compile(r"^[a-fA-F0-9]{32,64}$")
    url_re = re.compile(r"^https?://")
    email_re = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
    cve_re = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
    asn_re = re.compile(r"^AS\d+$", re.IGNORECASE)

    if ip_re.match(value):
        return "ip"
    if hash_re.match(value):
        return "hash"
    if url_re.match(value):
        return "url"
    if email_re.match(value):
        return "email"
    if cve_re.match(value):
        return "cve"
    if asn_re.match(value):
        return "asn"
    return "domain"


@router.get("/iocs", response_model=PaginatedResponse[IOCOut])
async def list_iocs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ioc_type: Optional[str] = None,
    search: Optional[str] = None,
    min_risk: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(IOC).where(IOC.is_archived == False)
    if ioc_type:
        query = query.where(IOC.ioc_type == ioc_type)
    if search:
        query = query.where(IOC.value.ilike(f"%{search}%"))
    if min_risk is not None:
        query = query.where(IOC.risk_score >= min_risk)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()

    query = query.order_by(IOC.last_seen.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


@router.post("/search")
async def search_ioc(
    value: str = Query(..., description="IP, domain, hash, URL, or email to search"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ioc_type = detect_ioc_type(value.strip())

    # Check cache in DB
    result = await db.execute(select(IOC).where(IOC.value == value.strip()))
    existing = result.scalar_one_or_none()

    enrichments = {}
    if ioc_type == "ip":
        enrichments = await enrich_ip(value.strip())
    elif ioc_type == "domain":
        enrichments = await enrich_domain(value.strip())
    elif ioc_type == "hash":
        enrichments = await enrich_hash(value.strip())
    elif ioc_type == "url":
        enrichments = await enrich_url(value.strip())
    elif ioc_type == "email":
        enrichments = await enrich_email(value.strip())
    elif ioc_type == "cve":
        enrichments = await enrich_cve(value.strip())
    elif ioc_type == "asn":
        enrichments = await enrich_asn(value.strip())

    risk_score = calculate_risk_score(enrichments)

    if existing:
        existing.risk_score = risk_score
        existing.last_seen = datetime.now(timezone.utc)
        existing.raw_data = enrichments
        existing.sources = list(enrichments.keys())
        ioc = existing
    else:
        ioc = IOC(
            value=value.strip(),
            ioc_type=ioc_type,
            risk_score=risk_score,
            raw_data=enrichments,
            sources=list(enrichments.keys()),
        )
        db.add(ioc)
        await db.flush()
        await db.refresh(ioc)

    return {"ioc": ioc, "enrichments": enrichments, "risk_score": risk_score}


@router.post("/iocs", response_model=IOCOut, dependencies=[Depends(require_analyst)])
async def create_ioc(
    body: IOCCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ioc = IOC(
        value=body.value,
        ioc_type=body.ioc_type or detect_ioc_type(body.value),
        analyst_notes=body.analyst_notes,
        created_by=current_user.id,
    )
    db.add(ioc)
    await db.flush()

    for tag in (body.tags or []):
        db.add(IOCTag(ioc_id=ioc.id, tag=tag, created_by=current_user.id))

    await db.refresh(ioc)
    return ioc


@router.post("/iocs/bulk", dependencies=[Depends(require_analyst)])
async def bulk_import_iocs(
    body: IOCBulkImport,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    created = 0
    for value in body.iocs:
        value = value.strip()
        if not value:
            continue
        existing = (await db.execute(select(IOC).where(IOC.value == value))).scalar_one_or_none()
        if existing:
            continue
        ioc = IOC(value=value, ioc_type=body.ioc_type, created_by=current_user.id)
        db.add(ioc)
        created += 1

    return {"created": created, "message": f"Imported {created} IOCs"}


@router.get("/iocs/{ioc_id}", response_model=IOCOut)
async def get_ioc(
    ioc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ioc = (await db.execute(select(IOC).where(IOC.id == ioc_id))).scalar_one_or_none()
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC not found")
    return ioc


@router.patch("/iocs/{ioc_id}", dependencies=[Depends(require_analyst)])
async def update_ioc(
    ioc_id: int,
    analyst_notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ioc = (await db.execute(select(IOC).where(IOC.id == ioc_id))).scalar_one_or_none()
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC not found")
    if analyst_notes is not None:
        ioc.analyst_notes = analyst_notes
    return ioc


@router.get("/feeds", response_model=List[ThreatFeedOut])
async def list_feeds(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ThreatFeed).order_by(ThreatFeed.name))
    return result.scalars().all()


@router.get("/feed-items", response_model=PaginatedResponse[FeedItemOut])
async def list_feed_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    feed_id: Optional[int] = None,
    severity: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(FeedItem).where(FeedItem.is_archived == False)
    if feed_id:
        query = query.where(FeedItem.feed_id == feed_id)
    if severity:
        query = query.where(FeedItem.severity == severity)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()
    query = query.order_by(FeedItem.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=math.ceil(total / page_size))


@router.post("/feeds/refresh", dependencies=[Depends(require_analyst)])
async def trigger_feed_refresh(background_tasks: BackgroundTasks):
    from app.tasks.threat_intel import fetch_all_feeds
    fetch_all_feeds.delay()
    return {"message": "Feed refresh triggered"}


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    total_iocs = (await db.execute(select(func.count()).select_from(IOC).where(IOC.is_archived == False))).scalar()
    iocs_24h = (await db.execute(select(func.count()).select_from(IOC).where(IOC.created_at >= since_24h))).scalar()
    critical_iocs = (await db.execute(select(func.count()).select_from(IOC).where(IOC.risk_score >= 75))).scalar()
    feed_items_24h = (await db.execute(select(func.count()).select_from(FeedItem).where(FeedItem.created_at >= since_24h))).scalar()

    return {
        "total_iocs": total_iocs,
        "iocs_24h": iocs_24h,
        "critical_iocs": critical_iocs,
        "feed_items_24h": feed_items_24h,
    }
