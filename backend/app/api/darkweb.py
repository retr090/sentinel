from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.darkweb import DarkWebKeyword, DarkWebMention, DarkWebScan, DarkWebAlert
from app.schemas.darkweb import (
    KeywordCreate, KeywordUpdate, KeywordResponse,
    MentionResponse, MentionUpdate,
    ScanResponse, BulkKeywordImport, ManualSearchRequest,
)
from app.services.darkweb.seed_keywords import seed_default_keywords
from app.core.celery_app import celery_app  # noqa: F401 — ensures app context for shared_task

router = APIRouter(prefix="/darkweb", tags=["darkweb"])


# ─── Keywords ─────────────────────────────────────────────────────────────────

@router.get("/keywords", response_model=List[KeywordResponse])
async def get_keywords(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(DarkWebKeyword)
    if category:
        query = query.where(DarkWebKeyword.category == category)
    if priority:
        query = query.where(DarkWebKeyword.priority == priority)
    if is_active is not None:
        query = query.where(DarkWebKeyword.is_active == is_active)
    if search:
        query = query.where(DarkWebKeyword.keyword.ilike(f"%{search}%"))

    query = query.order_by(
        desc(DarkWebKeyword.priority),
        desc(DarkWebKeyword.hit_count),
    ).offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/keywords/categories")
async def get_categories(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkWebKeyword.category, func.count(DarkWebKeyword.id).label("count"))
        .group_by(DarkWebKeyword.category)
        .order_by(desc("count"))
    )
    return [{"category": r[0], "count": r[1]} for r in result.all()]


@router.post("/keywords/seed")
async def seed_keywords(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Load default Sri Lanka keyword watchlist. Only works if no keywords exist yet."""
    count = await seed_default_keywords(db)
    return {"seeded": count, "message": f"Added {count} default keywords"}


@router.post("/keywords/bulk")
async def bulk_import_keywords(
    data: BulkKeywordImport,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    created = 0
    skipped = 0
    errors = []

    for kw_data in data.keywords:
        try:
            existing = await db.execute(
                select(DarkWebKeyword).where(DarkWebKeyword.keyword == kw_data.keyword)
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue
            kw = DarkWebKeyword(
                id=uuid.uuid4(),
                keyword=kw_data.keyword,
                aliases=kw_data.aliases,
                category=kw_data.category,
                priority=kw_data.priority,
                alert_mode=kw_data.alert_mode,
                sources=kw_data.sources,
                is_active=True,
                hit_count=0,
            )
            db.add(kw)
            created += 1
        except Exception as e:
            errors.append(f"{kw_data.keyword}: {str(e)}")

    await db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}


@router.post("/keywords", response_model=KeywordResponse)
async def create_keyword(
    data: KeywordCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(DarkWebKeyword).where(DarkWebKeyword.keyword == data.keyword)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Keyword '{data.keyword}' already exists")

    kw = DarkWebKeyword(
        id=uuid.uuid4(),
        keyword=data.keyword,
        aliases=data.aliases,
        category=data.category,
        priority=data.priority,
        alert_mode=data.alert_mode,
        sources=data.sources,
        notes=data.notes,
        created_by=str(getattr(current_user, "username", current_user.id)),
        is_active=True,
        hit_count=0,
    )
    db.add(kw)
    await db.commit()
    await db.refresh(kw)
    return kw


@router.put("/keywords/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: str,
    data: KeywordUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkWebKeyword).where(DarkWebKeyword.id == uuid.UUID(keyword_id))
    )
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(404, "Keyword not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(kw, field, value)

    kw.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(kw)
    return kw


@router.delete("/keywords/{keyword_id}")
async def delete_keyword(
    keyword_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkWebKeyword).where(DarkWebKeyword.id == uuid.UUID(keyword_id))
    )
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(404, "Keyword not found")
    await db.delete(kw)
    await db.commit()
    return {"success": True}


# ─── Mentions ─────────────────────────────────────────────────────────────────

@router.get("/mentions", response_model=List[MentionResponse])
async def get_mentions(
    source: Optional[str] = None,
    severity: Optional[str] = None,
    keyword: Optional[str] = None,
    is_reviewed: Optional[bool] = None,
    is_false_positive: Optional[bool] = False,
    days: int = Query(7, ge=1, le=90),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = select(DarkWebMention).where(
        and_(
            DarkWebMention.discovered_at >= cutoff,
            DarkWebMention.is_false_positive == is_false_positive,
        )
    )
    if source:
        query = query.where(DarkWebMention.source == source)
    if severity:
        query = query.where(DarkWebMention.severity == severity)
    if keyword:
        query = query.where(or_(
            DarkWebMention.keyword_matched.ilike(f"%{keyword}%"),
            DarkWebMention.title.ilike(f"%{keyword}%"),
            DarkWebMention.snippet.ilike(f"%{keyword}%"),
        ))
    if is_reviewed is not None:
        query = query.where(DarkWebMention.is_reviewed == is_reviewed)

    query = query.order_by(desc(DarkWebMention.discovered_at)).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/mentions/{mention_id}", response_model=MentionResponse)
async def get_mention(
    mention_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkWebMention).where(DarkWebMention.id == uuid.UUID(mention_id))
    )
    mention = result.scalar_one_or_none()
    if not mention:
        raise HTTPException(404, "Mention not found")
    return mention


@router.patch("/mentions/{mention_id}", response_model=MentionResponse)
async def update_mention(
    mention_id: str,
    data: MentionUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkWebMention).where(DarkWebMention.id == uuid.UUID(mention_id))
    )
    mention = result.scalar_one_or_none()
    if not mention:
        raise HTTPException(404, "Mention not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(mention, field, value)

    if data.is_reviewed:
        mention.reviewed_by = str(getattr(current_user, "username", current_user.id))
        mention.reviewed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(mention)
    return mention


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    total_kw = (await db.execute(select(func.count(DarkWebKeyword.id)))).scalar()
    active_kw = (await db.execute(
        select(func.count(DarkWebKeyword.id)).where(DarkWebKeyword.is_active == True)
    )).scalar()
    total_m = (await db.execute(
        select(func.count(DarkWebMention.id)).where(DarkWebMention.is_false_positive == False)
    )).scalar()
    unreviewed = (await db.execute(
        select(func.count(DarkWebMention.id)).where(
            and_(DarkWebMention.is_reviewed == False, DarkWebMention.is_false_positive == False)
        )
    )).scalar()
    critical = (await db.execute(
        select(func.count(DarkWebMention.id)).where(
            and_(DarkWebMention.severity == "CRITICAL", DarkWebMention.is_false_positive == False)
        )
    )).scalar()
    high = (await db.execute(
        select(func.count(DarkWebMention.id)).where(
            and_(DarkWebMention.severity == "HIGH", DarkWebMention.is_false_positive == False)
        )
    )).scalar()
    m_24h = (await db.execute(
        select(func.count(DarkWebMention.id)).where(DarkWebMention.discovered_at >= last_24h)
    )).scalar()
    m_7d = (await db.execute(
        select(func.count(DarkWebMention.id)).where(DarkWebMention.discovered_at >= last_7d)
    )).scalar()

    last_scan_result = await db.execute(
        select(DarkWebScan.completed_at)
        .where(DarkWebScan.status == "completed")
        .order_by(desc(DarkWebScan.completed_at))
        .limit(1)
    )
    last_scan = last_scan_result.scalar_one_or_none()

    source_counts = await db.execute(
        select(DarkWebMention.source, func.count(DarkWebMention.id).label("count"))
        .group_by(DarkWebMention.source)
    )

    return {
        "total_keywords": total_kw,
        "active_keywords": active_kw,
        "total_mentions": total_m,
        "unreviewed_mentions": unreviewed,
        "critical_mentions": critical,
        "high_mentions": high,
        "mentions_24h": m_24h,
        "mentions_7d": m_7d,
        "last_scan": last_scan.isoformat() if last_scan else None,
        "sources_status": {row[0]: row[1] for row in source_counts.all()},
    }


# ─── Scan History ─────────────────────────────────────────────────────────────

@router.get("/scans", response_model=List[ScanResponse])
async def get_scans(
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkWebScan).order_by(desc(DarkWebScan.created_at)).limit(limit)
    )
    return result.scalars().all()


# ─── Manual Search ────────────────────────────────────────────────────────────

@router.post("/search")
async def manual_search(
    req: ManualSearchRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a live dark web search across clearnet intelligence sources."""
    from app.services.darkweb.search import manual_search as run_manual_search
    from app.tasks.darkweb_tasks import _save_mention

    result = await run_manual_search(query=req.query, sources=req.sources)

    saved = 0
    for r in result.get("results", []):
        try:
            mention_data = {
                "keyword_matched": req.query,
                "source": r.get("source", "manual_search"),
                "source_url": r.get("url", ""),
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "severity": "MEDIUM",
                "category": "manual_search",
                "raw_data": r,
            }
            res = await _save_mention(db=db, mention_data=mention_data)
            if res == "new":
                saved += 1
        except Exception:
            continue

    result["saved_to_db"] = saved
    return result


# ─── Trigger Scan ─────────────────────────────────────────────────────────────

@router.post("/scan/trigger")
async def trigger_scan(
    scan_type: str = "ransomware",
    current_user=Depends(get_current_user),
):
    """Manually trigger a scan via Celery."""
    from app.tasks.darkweb_tasks import (
        scan_ransomware_manual,
        scan_rss_feeds,
        scan_paste_sites,
        scan_dark_web_search,
        scan_ransomware_historical,
        scan_forums,
    )

    task_map = {
        "ransomware": (scan_ransomware_manual, "Ransomware scan started"),
        "rss": (scan_rss_feeds, "RSS feed scan started"),
        "paste": (scan_paste_sites, "Paste site scan started"),
        "search": (scan_dark_web_search, "Dark web search scan started"),
        "historical": (scan_ransomware_historical, "Historical ransomware scan started — scanning all years for Sri Lanka victims"),
        "forums": (scan_forums, "Forum scan started — scanning Breached.st and other configured forums"),
    }

    if scan_type not in task_map:
        raise HTTPException(
            400,
            f"Unknown scan type '{scan_type}'. Valid: {list(task_map.keys())}",
        )

    task_func, message = task_map[scan_type]
    task = task_func.delay()
    return {
        "task_id": task.id,
        "scan_type": scan_type,
        "status": "queued",
        "message": message,
    }


# ─── Ransomware Tracker ────────────────────────────────────────────────────────

@router.get("/ransomware/victims")
async def get_ransomware_victims(
    days: int = Query(30, ge=1, le=365),
    country: Optional[str] = None,
    group: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days)
    sl_base = and_(
        DarkWebMention.source == "ransomware_live",
        DarkWebMention.keyword_matched != "global_tracker",
        DarkWebMention.discovered_at >= cutoff,
    )
    query = select(DarkWebMention).where(sl_base)
    if country:
        query = query.where(DarkWebMention.victim_country.ilike(f"%{country}%"))
    if group:
        query = query.where(DarkWebMention.threat_actor.ilike(f"%{group}%"))

    query = query.order_by(desc(DarkWebMention.discovered_at)).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    victims = result.scalars().all()

    group_stats = await db.execute(
        select(DarkWebMention.threat_actor, func.count(DarkWebMention.id).label("count"))
        .where(sl_base)
        .group_by(DarkWebMention.threat_actor)
        .order_by(desc("count"))
        .limit(10)
    )

    return {
        "victims": [
            {
                "id": str(v.id),
                "threat_actor": v.threat_actor,
                "victim_org": v.victim_org,
                "victim_country": v.victim_country,
                "severity": v.severity,
                "title": v.title,
                "snippet": v.snippet,
                "source_url": v.source_url,
                "keyword_matched": v.keyword_matched,
                "discovered_at": v.discovered_at.isoformat(),
                "published_at": v.published_at.isoformat() if v.published_at else None,
            }
            for v in victims
        ],
        "top_groups": [
            {"group": row[0], "count": row[1]}
            for row in group_stats.all()
        ],
        "total": len(victims),
    }


@router.get("/ransomware/stats")
async def get_ransomware_stats(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    last_7d = datetime.utcnow() - timedelta(days=7)
    last_30d = datetime.utcnow() - timedelta(days=30)

    sl_filter = and_(
        DarkWebMention.source == "ransomware_live",
        DarkWebMention.keyword_matched != "global_tracker",
    )

    total_sl = (await db.execute(
        select(func.count(DarkWebMention.id)).where(sl_filter)
    )).scalar()

    recent_7d = (await db.execute(
        select(func.count(DarkWebMention.id)).where(
            and_(sl_filter, DarkWebMention.discovered_at >= last_7d)
        )
    )).scalar()

    recent_30d = (await db.execute(
        select(func.count(DarkWebMention.id)).where(
            and_(sl_filter, DarkWebMention.discovered_at >= last_30d)
        )
    )).scalar()

    critical_high = (await db.execute(
        select(func.count(DarkWebMention.id)).where(
            and_(sl_filter, DarkWebMention.severity.in_(["CRITICAL", "HIGH"]))
        )
    )).scalar()

    top_groups = await db.execute(
        select(DarkWebMention.threat_actor, func.count(DarkWebMention.id).label("count"))
        .where(and_(sl_filter, DarkWebMention.discovered_at >= last_30d))
        .group_by(DarkWebMention.threat_actor)
        .order_by(desc("count"))
        .limit(10)
    )

    latest_result = await db.execute(
        select(DarkWebMention)
        .where(sl_filter)
        .order_by(desc(DarkWebMention.discovered_at))
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()

    return {
        "total_sl_victims": total_sl,
        "victims_last_7d": recent_7d,
        "victims_last_30d": recent_30d,
        "critical_high_hits": critical_high,
        "top_groups": [{"group": r[0], "count": r[1]} for r in top_groups.all()],
        "latest_victim": {
            "org": latest.victim_org,
            "country": latest.victim_country,
            "group": latest.threat_actor,
            "date": latest.discovered_at.isoformat(),
        } if latest else None,
    }


# ─── Forum Intelligence ───────────────────────────────────────────────────────

FORUM_SOURCES = ["breached_st", "forum_intelligence", "breached.st"]


@router.get("/forum-mentions")
async def get_forum_mentions(
    forum_id: Optional[str] = None,
    severity: Optional[str] = None,
    keyword: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """All mentions from authenticated forum sources (Breached.st etc.)."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Match any source containing "forum" OR any known forum source name
    forum_filter = and_(
        DarkWebMention.discovered_at >= cutoff,
        DarkWebMention.is_false_positive == False,
        DarkWebMention.source.in_(FORUM_SOURCES)
        | DarkWebMention.source.like("%forum%")
        | DarkWebMention.source.like("%breached%"),
    )

    query = select(DarkWebMention).where(forum_filter)

    if forum_id:
        query = query.where(DarkWebMention.source.ilike(f"%{forum_id}%"))
    if severity:
        query = query.where(DarkWebMention.severity == severity)
    if keyword:
        # Normalise common Sri Lanka aliases so either spelling finds the same data
        kw = keyword.strip()
        terms = [kw]
        kl = kw.lower()
        if kl == "srilanka":
            terms.append("sri lanka")
        elif kl == "sri lanka":
            terms.append("srilanka")
        elif kl in ("sl", "lk"):
            terms += ["sri lanka", "srilanka", ".lk"]

        conditions = []
        for t in terms:
            conditions += [
                DarkWebMention.keyword_matched.ilike(f"%{t}%"),
                DarkWebMention.title.ilike(f"%{t}%"),
                DarkWebMention.snippet.ilike(f"%{t}%"),
                DarkWebMention.victim_org.ilike(f"%{t}%"),
                DarkWebMention.source_url.ilike(f"%{t}%"),
            ]
        query = query.where(or_(*conditions))

    query = query.order_by(desc(DarkWebMention.discovered_at)).offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    mentions = result.scalars().all()

    # Aggregate stats across all-time (not capped by days filter)
    all_forum = and_(
        DarkWebMention.is_false_positive == False,
        DarkWebMention.source.in_(FORUM_SOURCES)
        | DarkWebMention.source.like("%forum%")
        | DarkWebMention.source.like("%breached%"),
    )
    total = (await db.execute(select(func.count(DarkWebMention.id)).where(all_forum))).scalar()
    critical_high = (await db.execute(
        select(func.count(DarkWebMention.id)).where(
            and_(all_forum, DarkWebMention.severity.in_(["CRITICAL", "HIGH"]))
        )
    )).scalar()
    unreviewed = (await db.execute(
        select(func.count(DarkWebMention.id)).where(
            and_(all_forum, DarkWebMention.is_reviewed == False)
        )
    )).scalar()

    # Per-source breakdown for the period
    src_counts = await db.execute(
        select(DarkWebMention.source, func.count(DarkWebMention.id).label("c"))
        .where(forum_filter)
        .group_by(DarkWebMention.source)
    )

    return {
        "mentions": [
            {
                "id": str(m.id),
                "title": m.title,
                "snippet": m.snippet,
                "source": m.source,
                "source_url": m.source_url,
                "severity": m.severity,
                "keyword_matched": m.keyword_matched,
                "threat_actor": m.threat_actor,
                "is_reviewed": m.is_reviewed,
                "analyst_notes": m.analyst_notes,
                "discovered_at": m.discovered_at.isoformat(),
                "raw_data": m.raw_data or {},
            }
            for m in mentions
        ],
        "stats": {
            "total": total,
            "critical_high": critical_high,
            "unreviewed": unreviewed,
            "by_source": {row[0]: row[1] for row in src_counts.all()},
        },
    }
