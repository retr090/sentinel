import io
import csv
import math
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.core.security import get_current_user, require_analyst
from app.models.user import User
from app.models.threat_intel import IOC, IOCTag, ThreatFeed, FeedItem, IOCBulkJob
from app.schemas.threat_intel import (
    IOCCreate, IOCOut, IOCLookupRequest, IOCLookupOut, IOCNotesUpdate,
    IOCBulkLookupRequest, IOCBulkJobOut,
    FeedItemOut, ThreatFeedOut, IOCBulkImport, ExportBulkRequest,
)
from app.schemas.common import PaginatedResponse
from app.services.threat_intel import (
    detect_ioc_type, enrich_ioc, calculate_risk_score,
    enrich_ip, enrich_domain, enrich_hash, enrich_url, enrich_email, enrich_cve, enrich_asn,
)
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/threat-intel", tags=["threat-intel"])


# ─────────────────────────────────────────────
# LOOKUP (new primary endpoint)
# ─────────────────────────────────────────────

@router.post("/lookup", response_model=IOCLookupOut)
async def lookup_ioc(
    body: IOCLookupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    value = body.value.strip()
    if not value:
        raise HTTPException(status_code=400, detail="IOC value is required")

    ioc_type = detect_ioc_type(value)
    enrichments = await enrich_ioc(value)
    risk_score, risk_level = calculate_risk_score(enrichments)

    existing = (await db.execute(select(IOC).where(IOC.value == value))).scalar_one_or_none()
    if existing:
        existing.risk_score = risk_score
        existing.risk_level = risk_level
        existing.last_seen = datetime.now(timezone.utc)
        existing.raw_data = enrichments
        existing.sources = list(enrichments.keys())
        ioc = existing
    else:
        ioc = IOC(
            value=value,
            ioc_type=ioc_type,
            risk_score=risk_score,
            risk_level=risk_level,
            raw_data=enrichments,
            sources=list(enrichments.keys()),
            created_by=current_user.id,
        )
        db.add(ioc)
        await db.flush()
        await db.refresh(ioc)

    return IOCLookupOut(
        ioc=IOCOut.model_validate(ioc),
        enrichments=enrichments,
        risk_score=risk_score,
        risk_level=risk_level,
    )


# ─────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────

@router.get("/history", response_model=PaginatedResponse[IOCOut])
async def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    risk_level: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(IOC).where(IOC.is_archived == False)

    if type:
        if type == "hash":
            query = query.where(
                or_(IOC.ioc_type == "hash", IOC.ioc_type.like("hash_%"))
            )
        else:
            query = query.where(IOC.ioc_type == type)
    if risk_level:
        query = query.where(IOC.risk_level == risk_level)
    if search:
        query = query.where(IOC.value.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()

    query = query.order_by(IOC.last_seen.desc()).offset((page - 1) * limit).limit(limit)
    items = (await db.execute(query)).scalars().all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=limit,
        pages=math.ceil(total / limit) if total else 1,
    )


# ─────────────────────────────────────────────
# SINGLE IOC
# ─────────────────────────────────────────────

@router.get("/ioc/{ioc_id}", response_model=IOCLookupOut)
async def get_ioc(
    ioc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ioc = (await db.execute(select(IOC).where(IOC.id == ioc_id, IOC.is_archived == False))).scalar_one_or_none()
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC not found")
    return IOCLookupOut(
        ioc=IOCOut.model_validate(ioc),
        enrichments=ioc.raw_data or {},
        risk_score=ioc.risk_score,
        risk_level=ioc.risk_level or "clean",
    )


@router.delete("/ioc/{ioc_id}")
async def archive_ioc(
    ioc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ioc = (await db.execute(select(IOC).where(IOC.id == ioc_id))).scalar_one_or_none()
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC not found")
    ioc.is_archived = True
    return {"message": "IOC archived"}


@router.patch("/ioc/{ioc_id}/notes")
async def update_notes(
    ioc_id: int,
    body: IOCNotesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ioc = (await db.execute(select(IOC).where(IOC.id == ioc_id))).scalar_one_or_none()
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC not found")
    ioc.analyst_notes = body.notes
    return {"message": "Notes updated"}


# ─────────────────────────────────────────────
# BULK LOOKUP
# ─────────────────────────────────────────────

@router.post("/bulk", response_model=IOCBulkJobOut)
async def start_bulk_lookup(
    body: IOCBulkLookupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    iocs = [v.strip() for v in body.iocs if v.strip()]
    if not iocs:
        raise HTTPException(status_code=400, detail="No IOC values provided")
    if len(iocs) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 IOCs per bulk job")

    job = IOCBulkJob(
        status="pending",
        total=len(iocs),
        processed=0,
        results=[],
        created_by=current_user.id,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    import asyncio
    from app.core.celery_app import celery_app
    job_id_val = job.id
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: celery_app.send_task(
            'app.tasks.threat_intel.run_bulk_ioc_lookup',
            args=[job_id_val, iocs, current_user.id],
            queue='feeds',
        )
    )

    return IOCBulkJobOut.model_validate(job)


@router.get("/bulk/{job_id}", response_model=IOCBulkJobOut)
async def get_bulk_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = (await db.execute(select(IOCBulkJob).where(IOCBulkJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Bulk job not found")
    return IOCBulkJobOut.model_validate(job)


# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────

def _ioc_to_csv_row(ioc: IOC) -> list:
    return [
        ioc.id,
        ioc.value,
        ioc.ioc_type,
        ioc.risk_score,
        ioc.risk_level or "clean",
        ",".join(ioc.sources or []),
        ioc.analyst_notes or "",
        ioc.first_seen.isoformat() if ioc.first_seen else "",
        ioc.last_seen.isoformat() if ioc.last_seen else "",
    ]


CSV_HEADERS = ["id", "value", "type", "risk_score", "risk_level", "sources", "analyst_notes", "first_seen", "last_seen"]


@router.get("/export/{ioc_id}")
async def export_ioc_csv(
    ioc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ioc = (await db.execute(select(IOC).where(IOC.id == ioc_id))).scalar_one_or_none()
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)
    writer.writerow(_ioc_to_csv_row(ioc))

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="ioc_{ioc_id}.csv"'},
    )


@router.post("/export/bulk")
async def export_bulk_csv(
    body: ExportBulkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")

    result = await db.execute(select(IOC).where(IOC.id.in_(body.ids)))
    iocs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)
    for ioc in iocs:
        writer.writerow(_ioc_to_csv_row(ioc))

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="iocs_export.csv"'},
    )


# ─────────────────────────────────────────────
# LEGACY SEARCH (kept for backward compat)
# ─────────────────────────────────────────────

@router.post("/search")
async def search_ioc(
    value: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ioc_type = detect_ioc_type(value.strip())
    enrichments = await enrich_ioc(value.strip())
    risk_score, risk_level = calculate_risk_score(enrichments)

    existing = (await db.execute(select(IOC).where(IOC.value == value.strip()))).scalar_one_or_none()
    if existing:
        existing.risk_score = risk_score
        existing.risk_level = risk_level
        existing.last_seen = datetime.now(timezone.utc)
        existing.raw_data = enrichments
        existing.sources = list(enrichments.keys())
        ioc = existing
    else:
        ioc = IOC(
            value=value.strip(),
            ioc_type=ioc_type,
            risk_score=risk_score,
            risk_level=risk_level,
            raw_data=enrichments,
            sources=list(enrichments.keys()),
        )
        db.add(ioc)
        await db.flush()
        await db.refresh(ioc)

    return {"ioc": ioc, "enrichments": enrichments, "risk_score": risk_score}


# ─────────────────────────────────────────────
# IOC CRUD (legacy)
# ─────────────────────────────────────────────

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
        pages=math.ceil(total / page_size) if total else 1,
    )


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
async def get_ioc_legacy(
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


# ─────────────────────────────────────────────
# FEEDS
# ─────────────────────────────────────────────

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

    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 1,
    )


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
    critical_iocs = (await db.execute(select(func.count()).select_from(IOC).where(IOC.risk_score >= 75, IOC.is_archived == False))).scalar()
    feed_items_24h = (await db.execute(select(func.count()).select_from(FeedItem).where(FeedItem.created_at >= since_24h))).scalar()

    return {
        "total_iocs": total_iocs,
        "iocs_24h": iocs_24h,
        "critical_iocs": critical_iocs,
        "feed_items_24h": feed_items_24h,
    }
