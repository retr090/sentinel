from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.core.security import get_current_user, require_analyst
from app.models.user import User
from app.models.dark_web import WatchlistKeyword, DarkWebMention, BreachResult, PasteHit
from app.schemas.common import PaginatedResponse
from pydantic import BaseModel
import math
import httpx

router = APIRouter(prefix="/dark-web", tags=["dark-web"])

TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class KeywordCreate(BaseModel):
    keyword: str
    category: Optional[str] = "general"
    severity: str = "MEDIUM"


class BreachLookupRequest(BaseModel):
    query: str
    query_type: str = "email"


class MentionOut(BaseModel):
    id: int
    keyword: str
    source: Optional[str]
    source_url: Optional[str]
    title: Optional[str]
    snippet: Optional[str]
    severity: str
    is_acknowledged: bool
    found_at: datetime

    class Config:
        from_attributes = True


class KeywordOut(BaseModel):
    id: int
    keyword: str
    category: Optional[str]
    severity: str
    is_active: bool
    last_scanned: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/keywords", response_model=List[KeywordOut])
async def list_keywords(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WatchlistKeyword).order_by(WatchlistKeyword.created_at.desc()))
    return result.scalars().all()


@router.post("/keywords", response_model=KeywordOut, dependencies=[Depends(require_analyst)])
async def create_keyword(
    body: KeywordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(select(WatchlistKeyword).where(WatchlistKeyword.keyword == body.keyword))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Keyword already exists")
    kw = WatchlistKeyword(
        keyword=body.keyword,
        category=body.category,
        severity=body.severity,
        created_by=current_user.id,
    )
    db.add(kw)
    await db.flush()
    await db.refresh(kw)
    return kw


@router.delete("/keywords/{kw_id}", dependencies=[Depends(require_analyst)])
async def delete_keyword(kw_id: int, db: AsyncSession = Depends(get_db)):
    kw = (await db.execute(select(WatchlistKeyword).where(WatchlistKeyword.id == kw_id))).scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    await db.delete(kw)
    return {"message": "Keyword deleted"}


@router.get("/mentions", response_model=PaginatedResponse[MentionOut])
async def list_mentions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    severity: Optional[str] = None,
    unacknowledged_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(DarkWebMention).where(DarkWebMention.is_archived == False)
    if keyword:
        query = query.where(DarkWebMention.keyword.ilike(f"%{keyword}%"))
    if severity:
        query = query.where(DarkWebMention.severity == severity)
    if unacknowledged_only:
        query = query.where(DarkWebMention.is_acknowledged == False)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(DarkWebMention.found_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=math.ceil(total / page_size))


@router.post("/mentions/{mention_id}/acknowledge", dependencies=[Depends(require_analyst)])
async def acknowledge_mention(mention_id: int, db: AsyncSession = Depends(get_db)):
    mention = (await db.execute(select(DarkWebMention).where(DarkWebMention.id == mention_id))).scalar_one_or_none()
    if not mention:
        raise HTTPException(status_code=404, detail="Mention not found")
    mention.is_acknowledged = True
    return {"message": "Acknowledged"}


@router.post("/breach-lookup")
async def breach_lookup(
    body: BreachLookupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.dark_web import lookup_hibp, lookup_paste_sites
    results = {}

    if body.query_type in ("email", "domain"):
        hibp_results = await lookup_hibp(body.query, body.query_type)
        results["hibp"] = hibp_results

    paste_results = await lookup_paste_sites(body.query)
    results["paste_sites"] = paste_results

    return results


@router.post("/scan-now", dependencies=[Depends(require_analyst)])
async def trigger_scan():
    from app.tasks.dark_web import scan_watchlist
    scan_watchlist.delay()
    return {"message": "Dark web scan triggered"}


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    total_mentions = (await db.execute(select(func.count()).select_from(DarkWebMention).where(DarkWebMention.is_archived == False))).scalar()
    mentions_24h = (await db.execute(select(func.count()).select_from(DarkWebMention).where(DarkWebMention.found_at >= since_24h))).scalar()
    keywords_active = (await db.execute(select(func.count()).select_from(WatchlistKeyword).where(WatchlistKeyword.is_active == True))).scalar()
    breaches_total = (await db.execute(select(func.count()).select_from(BreachResult))).scalar()

    return {
        "total_mentions": total_mentions,
        "mentions_24h": mentions_24h,
        "keywords_active": keywords_active,
        "breaches_total": breaches_total,
    }
