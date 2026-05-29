from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from typing import Optional, List, Any, Dict
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.core.security import get_current_user, require_analyst
from app.models.user import User
from app.models.news import NewsSource, NewsArticle, NewsKeyword, NewsAlert
from app.schemas.common import PaginatedResponse
from pydantic import BaseModel
import math

router = APIRouter(prefix="/news", tags=["news"])


class NewsSourceCreate(BaseModel):
    name: str
    url: str
    source_type: str = "rss"
    category: Optional[str] = "general"
    language: str = "en"


class NewsKeywordCreate(BaseModel):
    keyword: str
    category: Optional[str] = "general"
    alert_threshold: int = 10


class ArticleOut(BaseModel):
    id: int
    source_id: Optional[int]
    title: str
    url: Optional[str]
    content_snippet: Optional[str]
    full_text: Optional[str]
    author: Optional[str]
    category: Optional[str]
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    keywords_matched: Optional[List[str]]
    language: str
    relevance_score: Optional[float]
    relevance_label: Optional[str]
    ai_analysis: Optional[Dict[str, Any]] = None
    published_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/articles", response_model=PaginatedResponse[ArticleOut])
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    sentiment: Optional[str] = None,
    relevance: Optional[str] = None,
    language: Optional[str] = None,
    since_hours: int = Query(24, ge=1, le=720),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    query = select(NewsArticle).where(
        and_(NewsArticle.is_archived == False, NewsArticle.created_at >= since)
    )
    if category:
        query = query.where(NewsArticle.category == category)
    if keyword:
        query = query.where(NewsArticle.title.ilike(f"%{keyword}%"))
    if sentiment:
        query = query.where(NewsArticle.sentiment_label == sentiment)
    if relevance:
        query = query.where(NewsArticle.relevance_label == relevance)
    if language:
        query = query.where(NewsArticle.language == language)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(NewsArticle.published_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=math.ceil(total / page_size))


@router.get("/sources")
async def list_sources(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewsSource).order_by(NewsSource.name))
    return result.scalars().all()


@router.post("/sources", dependencies=[Depends(require_analyst)])
async def create_source(body: NewsSourceCreate, db: AsyncSession = Depends(get_db)):
    source = NewsSource(**body.model_dump())
    db.add(source)
    await db.flush()
    await db.refresh(source)
    return source


@router.get("/keywords")
async def list_keywords(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewsKeyword).where(NewsKeyword.is_active == True))
    return result.scalars().all()


@router.post("/keywords", dependencies=[Depends(require_analyst)])
async def create_keyword(
    body: NewsKeywordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kw = NewsKeyword(**body.model_dump(), created_by=current_user.id)
    db.add(kw)
    await db.flush()
    await db.refresh(kw)
    return kw


@router.get("/timeline")
async def get_timeline(
    days: int = Query(7, ge=1, le=30),
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    day_trunc = func.date_trunc(text("'day'"), NewsArticle.published_at)
    query = select(
        day_trunc.label("date"),
        func.count().label("count"),
        NewsArticle.category,
    ).where(
        and_(NewsArticle.published_at >= since, NewsArticle.is_archived == False)
    ).group_by(text("1"), NewsArticle.category)

    if category:
        query = query.where(NewsArticle.category == category)

    result = await db.execute(query.order_by(text("1")))
    rows = result.all()
    return [{"date": r.date.isoformat() if r.date else None, "count": r.count, "category": r.category} for r in rows]


@router.post("/fetch-now", dependencies=[Depends(require_analyst)])
async def trigger_fetch():
    from app.tasks.news import fetch_all_news
    fetch_all_news.delay()
    return {"message": "News fetch triggered"}


@router.post("/score-now", dependencies=[Depends(require_analyst)])
async def trigger_scoring():
    from app.tasks.news import score_news_relevance
    score_news_relevance.delay()
    return {"message": "Relevance scoring triggered"}


@router.get("/alerts")
async def list_alerts(
    acknowledged: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(NewsAlert).order_by(NewsAlert.triggered_at.desc()).limit(50)
    if acknowledged is not None:
        query = query.where(NewsAlert.is_acknowledged == acknowledged)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_analyst)])
async def acknowledge_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewsAlert).where(NewsAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_acknowledged = True
    await db.commit()
    return {"message": "Alert acknowledged"}


@router.get("/trending-keywords")
async def get_trending_keywords(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from collections import Counter
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(NewsArticle.keywords_matched)
        .where(NewsArticle.created_at >= since, NewsArticle.is_archived == False,
               NewsArticle.keywords_matched.isnot(None))
    )
    counter: Counter = Counter()
    for kws in result.scalars().all():
        if isinstance(kws, list):
            for kw in kws:
                if kw:
                    counter[str(kw)] += 1
    return [{"keyword": kw, "count": count} for kw, count in counter.most_common(limit)]


@router.get("/stats")
async def get_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    total = (await db.execute(select(func.count()).select_from(NewsArticle).where(NewsArticle.is_archived == False))).scalar()
    articles_24h = (await db.execute(select(func.count()).select_from(NewsArticle).where(NewsArticle.created_at >= since_24h))).scalar()
    sources_active = (await db.execute(select(func.count()).select_from(NewsSource).where(NewsSource.is_active == True))).scalar()
    alerts_open = (await db.execute(select(func.count()).select_from(NewsAlert).where(NewsAlert.is_acknowledged == False))).scalar()

    category_counts: dict = {}
    for cat in ('regional', 'cyber', 'military', 'general', 'politics'):
        n = (await db.execute(select(func.count()).select_from(NewsArticle).where(
            NewsArticle.is_archived == False, NewsArticle.category == cat, NewsArticle.created_at >= since_24h
        ))).scalar() or 0
        if n:
            category_counts[cat] = n

    language_counts: dict = {}
    for lang in ('en', 'si', 'ta'):
        n = (await db.execute(select(func.count()).select_from(NewsArticle).where(
            NewsArticle.is_archived == False, NewsArticle.language == lang, NewsArticle.created_at >= since_24h
        ))).scalar() or 0
        if n:
            language_counts[lang] = n

    return {
        "total_articles": total, "articles_24h": articles_24h,
        "sources_active": sources_active, "alerts_open": alerts_open,
        "category_counts": category_counts, "language_counts": language_counts,
    }
