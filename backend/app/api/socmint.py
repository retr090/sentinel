from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List, Any, Dict
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.core.security import get_current_user, require_analyst
from app.models.user import User
from app.models.socmint import SocialKeyword, SocialPost, SocialAccount, SocialAlert
from app.schemas.common import PaginatedResponse
from pydantic import BaseModel
import math

router = APIRouter(prefix="/socmint", tags=["socmint"])


class SocialKeywordCreate(BaseModel):
    keyword: str
    platforms: Optional[List[str]] = ["reddit"]
    alert_on_spike: bool = True
    spike_threshold: int = 50


class SocialKeywordUpdate(BaseModel):
    keyword: Optional[str] = None
    platforms: Optional[List[str]] = None
    alert_on_spike: Optional[bool] = None
    spike_threshold: Optional[int] = None
    is_active: Optional[bool] = None


class PostOut(BaseModel):
    id: int
    platform: str
    content: Optional[str]
    url: Optional[str]
    keyword_matched: Optional[str]
    likes: int
    shares: int
    comments: int
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    raw_data: Optional[Dict[str, Any]] = None
    posted_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/keywords")
async def list_keywords(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SocialKeyword).order_by(SocialKeyword.created_at.desc()))
    return result.scalars().all()


@router.post("/keywords", dependencies=[Depends(require_analyst)])
async def create_keyword(
    body: SocialKeywordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kw = SocialKeyword(**body.model_dump(), created_by=current_user.id)
    db.add(kw)
    await db.flush()
    await db.refresh(kw)
    return kw


@router.delete("/keywords/{kw_id}", dependencies=[Depends(require_analyst)])
async def delete_keyword(kw_id: int, db: AsyncSession = Depends(get_db)):
    kw = (await db.execute(select(SocialKeyword).where(SocialKeyword.id == kw_id))).scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(kw)
    return {"message": "Deleted"}


@router.patch("/keywords/{kw_id}", dependencies=[Depends(require_analyst)])
async def update_keyword(kw_id: int, body: SocialKeywordUpdate, db: AsyncSession = Depends(get_db)):
    kw = (await db.execute(select(SocialKeyword).where(SocialKeyword.id == kw_id))).scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Not found")
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(kw, field, value)
    await db.flush()
    await db.refresh(kw)
    return kw


@router.get("/alerts")
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    acknowledged: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(SocialAlert)
    if acknowledged is not None:
        query = query.where(SocialAlert.is_acknowledged == acknowledged)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(SocialAlert.triggered_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": math.ceil(total / page_size)}


@router.post("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_analyst)])
async def acknowledge_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    alert = (await db.execute(select(SocialAlert).where(SocialAlert.id == alert_id))).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Not found")
    alert.is_acknowledged = True
    return {"message": "Acknowledged"}


@router.get("/posts", response_model=PaginatedResponse[PostOut])
async def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: Optional[str] = None,
    keyword: Optional[str] = None,
    since_hours: int = Query(24, ge=1, le=720),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    query = select(SocialPost).where(SocialPost.created_at >= since, SocialPost.is_archived == False)
    if platform:
        query = query.where(SocialPost.platform == platform)
    if keyword:
        query = query.where(SocialPost.keyword_matched == keyword)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(SocialPost.posted_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=math.ceil(total / page_size))


@router.post("/scan-now", dependencies=[Depends(require_analyst)])
async def trigger_scan():
    from app.core.celery_app import celery_app
    celery_app.send_task("app.tasks.socmint.scan_all_keywords", queue="feeds")
    return {"message": "SOCMINT scan triggered"}


@router.get("/reddit/status")
async def reddit_status(current_user: User = Depends(get_current_user)):
    from app.core.config import settings
    return {
        "configured": bool(settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET),
        "user_agent": settings.REDDIT_USER_AGENT,
        "fallback": "public_json",
    }


@router.get("/stats")
async def get_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    total_posts = (await db.execute(select(func.count()).select_from(SocialPost).where(SocialPost.is_archived == False))).scalar()
    posts_24h = (await db.execute(select(func.count()).select_from(SocialPost).where(SocialPost.created_at >= since_24h))).scalar()
    keywords_active = (await db.execute(select(func.count()).select_from(SocialKeyword).where(SocialKeyword.is_active == True))).scalar()
    return {"total_posts": total_posts, "posts_24h": posts_24h, "keywords_active": keywords_active}
