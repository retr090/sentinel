import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_analyst
from app.models.darkweb import DarkWebMention, DarkWebScan

router = APIRouter(prefix="/darkweb", tags=["dark-web-intelligence"])


FORUM_SOURCES = ["breached_st", "forum_intelligence", "breached.st"]


def _parse_ransomware_source_date(value):
    if not value:
        return None
    value = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value[:26] if "+" not in value and len(value) > 26 else value).replace(tzinfo=None)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value[:19], fmt)
            except ValueError:
                continue
    return None


def _ransomware_feed_posted_at(mention: DarkWebMention):
    raw = mention.raw_data if isinstance(mention.raw_data, dict) else {}
    for key in ("published", "published_at", "posted_at", "post_date", "date", "attackdate"):
        parsed = _parse_ransomware_source_date(raw.get(key))
        if parsed:
            return parsed
    return mention.feed_posted_at or mention.published_at or mention.discovered_at


def _forum_filter(days: Optional[int] = None):
    filters = [
        DarkWebMention.is_false_positive == False,
        DarkWebMention.source.in_(FORUM_SOURCES)
        | DarkWebMention.source.like("%forum%")
        | DarkWebMention.source.like("%breached%"),
    ]
    if days is not None:
        filters.append(DarkWebMention.feed_posted_at >= datetime.utcnow() - timedelta(days=days))
    return and_(*filters)


def _ransomware_filter():
    return and_(
        DarkWebMention.source == "ransomware_live",
        DarkWebMention.keyword_matched != "global_tracker",
    )


def _ransomware_sector(mention: DarkWebMention) -> str:
    raw = mention.raw_data if isinstance(mention.raw_data, dict) else {}
    text = " ".join(str(v or "") for v in (
        mention.victim_org,
        mention.title,
        mention.snippet,
        raw.get("description"),
        raw.get("activity"),
        raw.get("sector"),
        raw.get("website"),
    )).lower()
    sector_rules = [
        ("Government", ("gov.lk", "ministry", "department", "authority", "municipal", "provincial")),
        ("Banking/Finance", ("bank", "finance", "insurance", "financial", "credit", "securities")),
        ("Healthcare", ("health", "hospital", "medical", "clinic", "pharma")),
        ("Telecom/Technology", ("telecom", "technology", "software", "it ", "internet", "network", "lankacom")),
        ("Manufacturing", ("manufacturing", "factory", "packaging", "apparel", "holdings", "products", "food")),
        ("Travel/Hospitality", ("travel", "tour", "hotel", "hospitality", "airline")),
        ("Education", ("university", "college", "school", "education", "campus")),
    ]
    for sector, keywords in sector_rules:
        if any(keyword in text for keyword in keywords):
            return sector
    return "Unknown"


def _ransomware_data_status(mention: DarkWebMention) -> str:
    raw = mention.raw_data if isinstance(mention.raw_data, dict) else {}
    text = " ".join(str(v or "") for v in (mention.snippet, mention.full_content, raw.get("description"))).lower()
    if any(term in text for term in ("exfiltrated data : yes", "download", "leak", "published", "dump")):
        return "Data exposed"
    if any(term in text for term in ("encrypted data", "claimed", "victim")):
        return "Claimed"
    return "Unknown"


def _month_key(value: datetime | None) -> str:
    return value.strftime("%Y-%m") if value else "unknown"


@router.get("/stats")
async def get_leak_intel_stats(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since_24h = datetime.utcnow() - timedelta(hours=24)
    ransomware = _ransomware_filter()
    forums = _forum_filter()

    ransomware_24h = (await db.execute(
        select(func.count(DarkWebMention.id)).where(
            and_(ransomware, DarkWebMention.discovered_at >= since_24h)
        )
    )).scalar()
    forum_24h = (await db.execute(
        select(func.count(DarkWebMention.id)).where(
            and_(forums, DarkWebMention.discovered_at >= since_24h)
        )
    )).scalar()
    unreviewed_forums = (await db.execute(
        select(func.count(DarkWebMention.id)).where(
            and_(forums, DarkWebMention.is_reviewed == False)
        )
    )).scalar()
    unread_ransomware = (await db.execute(
        select(func.count(DarkWebMention.id)).where(
            and_(ransomware, DarkWebMention.analyst_seen_at.is_(None))
        )
    )).scalar()

    return {
        "mentions_24h": (ransomware_24h or 0) + (forum_24h or 0),
        "ransomware_24h": ransomware_24h or 0,
        "forum_mentions_24h": forum_24h or 0,
        "unreviewed": (unreviewed_forums or 0) + (unread_ransomware or 0),
    }


@router.get("/scans")
async def get_scans(
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkWebScan)
        .where(DarkWebScan.scan_type.in_(["ransomware", "ransomware_historical", "forums"]))
        .order_by(desc(DarkWebScan.created_at))
        .limit(limit)
    )
    return [
        {
            "id": str(scan.id),
            "scan_type": scan.scan_type,
            "source": scan.source,
            "status": scan.status,
            "keywords_scanned": scan.keywords_scanned,
            "mentions_found": scan.mentions_found,
            "new_mentions": scan.new_mentions,
            "error_message": scan.error_message,
            "started_at": scan.started_at.isoformat() if scan.started_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            "duration_seconds": scan.duration_seconds,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
        }
        for scan in result.scalars().all()
    ]


@router.post("/scan/trigger")
async def trigger_scan(
    scan_type: str = "ransomware",
    current_user=Depends(require_analyst),
):
    from app.core.celery_app import celery_app

    task_map = {
        "ransomware": ("app.tasks.darkweb_tasks.scan_ransomware_manual", "Ransomware scan started"),
        "historical": ("app.tasks.darkweb_tasks.scan_ransomware_historical", "Historical ransomware scan started"),
        "forums": ("app.tasks.darkweb_tasks.scan_forums", "Forum intelligence scan started"),
    }
    if scan_type not in task_map:
        raise HTTPException(400, f"Unsupported scan type '{scan_type}'. Valid: {list(task_map.keys())}")

    task_name, message = task_map[scan_type]
    task = celery_app.send_task(task_name, queue="darkweb")
    return {"task_id": task.id, "scan_type": scan_type, "status": "queued", "message": message}


@router.patch("/mentions/{mention_id}")
async def update_mention(
    mention_id: str,
    updates: dict,
    current_user=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(DarkWebMention).where(DarkWebMention.id == uuid.UUID(mention_id)))
    mention = result.scalar_one_or_none()
    if not mention:
        raise HTTPException(404, "Mention not found")

    allowed = {"is_reviewed", "is_false_positive", "triage_status", "analyst_notes"}
    for field, value in updates.items():
        if field in allowed:
            setattr(mention, field, value)
    if updates.get("is_reviewed") or updates.get("is_false_positive"):
        mention.reviewed_by = str(getattr(current_user, "username", current_user.id))
        mention.reviewed_at = datetime.utcnow()
    if updates.get("triage_status") == "false_positive":
        mention.is_false_positive = True
    if updates.get("is_false_positive"):
        mention.triage_status = "false_positive"

    await db.commit()
    await db.refresh(mention)
    return _serialize_mention(mention)


@router.get("/ransomware/victims")
async def get_ransomware_victims(
    days: int = Query(30, ge=0, le=3650),
    country: Optional[str] = None,
    group: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    posted_at_expr = func.coalesce(
        DarkWebMention.feed_posted_at,
        DarkWebMention.published_at,
        DarkWebMention.discovered_at,
    )
    filters = [_ransomware_filter()]
    if days > 0:
        filters.append(posted_at_expr >= datetime.utcnow() - timedelta(days=days))
    query = select(DarkWebMention).where(and_(*filters))
    if country:
        query = query.where(DarkWebMention.victim_country.ilike(f"%{country}%"))
    if group:
        query = query.where(DarkWebMention.threat_actor.ilike(f"%{group}%"))

    result = await db.execute(
        query.order_by(desc(posted_at_expr), desc(DarkWebMention.discovered_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    victims = result.scalars().all()

    group_stats = await db.execute(
        select(DarkWebMention.threat_actor, func.count(DarkWebMention.id).label("count"))
        .where(and_(*filters))
        .group_by(DarkWebMention.threat_actor)
        .order_by(desc("count"))
        .limit(10)
    )

    return {
        "victims": [_serialize_ransomware_victim(v) for v in victims],
        "top_groups": [{"group": row[0], "count": row[1]} for row in group_stats.all()],
        "total": len(victims),
    }


@router.get("/ransomware/stats")
async def get_ransomware_stats(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    last_7d = datetime.utcnow() - timedelta(days=7)
    last_30d = datetime.utcnow() - timedelta(days=30)
    posted_at_expr = func.coalesce(
        DarkWebMention.feed_posted_at,
        DarkWebMention.published_at,
        DarkWebMention.discovered_at,
    )
    ransomware = _ransomware_filter()

    total = (await db.execute(select(func.count(DarkWebMention.id)).where(ransomware))).scalar()
    unread = (await db.execute(select(func.count(DarkWebMention.id)).where(and_(ransomware, DarkWebMention.analyst_seen_at.is_(None))))).scalar()
    recent_7d = (await db.execute(select(func.count(DarkWebMention.id)).where(and_(ransomware, posted_at_expr >= last_7d)))).scalar()
    recent_30d = (await db.execute(select(func.count(DarkWebMention.id)).where(and_(ransomware, posted_at_expr >= last_30d)))).scalar()
    critical_high = (await db.execute(select(func.count(DarkWebMention.id)).where(and_(ransomware, DarkWebMention.severity.in_(["CRITICAL", "HIGH"]))))).scalar()

    top_groups = await db.execute(
        select(DarkWebMention.threat_actor, func.count(DarkWebMention.id).label("count"))
        .where(and_(ransomware, posted_at_expr >= last_30d))
        .group_by(DarkWebMention.threat_actor)
        .order_by(desc("count"))
        .limit(10)
    )
    latest = (await db.execute(
        select(DarkWebMention).where(ransomware).order_by(desc(posted_at_expr), desc(DarkWebMention.discovered_at)).limit(1)
    )).scalar_one_or_none()

    return {
        "total_victims": total or 0,
        "unread_ransomware_count": unread or 0,
        "last_7_days": recent_7d or 0,
        "last_30_days": recent_30d or 0,
        "critical_high": critical_high or 0,
        "total_sl_victims": total or 0,
        "victims_last_7d": recent_7d or 0,
        "victims_last_30d": recent_30d or 0,
        "critical_high_hits": critical_high or 0,
        "top_groups": [{"group": r[0], "count": r[1]} for r in top_groups.all()],
        "latest_victim": {
            "org": latest.victim_org,
            "country": latest.victim_country,
            "group": latest.threat_actor,
            "date": _ransomware_feed_posted_at(latest).isoformat(),
        } if latest else None,
    }


@router.get("/ransomware/summary")
async def get_ransomware_summary(
    days: int = Query(365, ge=0, le=3650),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    posted_at_expr = func.coalesce(
        DarkWebMention.feed_posted_at,
        DarkWebMention.published_at,
        DarkWebMention.discovered_at,
    )
    filters = [_ransomware_filter()]
    if days > 0:
        filters.append(posted_at_expr >= datetime.utcnow() - timedelta(days=days))
    result = await db.execute(select(DarkWebMention).where(and_(*filters)))
    rows = result.scalars().all()

    sectors: dict[str, int] = {}
    statuses: dict[str, int] = {}
    timeline: dict[str, int] = {}
    groups: dict[str, dict] = {}
    for row in rows:
        sector = _ransomware_sector(row)
        status = _ransomware_data_status(row)
        posted_at = _ransomware_feed_posted_at(row)
        group = row.threat_actor or "Unknown"
        sectors[sector] = sectors.get(sector, 0) + 1
        statuses[status] = statuses.get(status, 0) + 1
        timeline[_month_key(posted_at)] = timeline.get(_month_key(posted_at), 0) + 1
        group_row = groups.setdefault(group, {"group": group, "victims": 0, "critical_high": 0, "latest_seen": None})
        group_row["victims"] += 1
        if row.severity in ("CRITICAL", "HIGH"):
            group_row["critical_high"] += 1
        if posted_at and (group_row["latest_seen"] is None or posted_at > group_row["latest_seen"]):
            group_row["latest_seen"] = posted_at

    return {
        "total": len(rows),
        "by_sector": [{"sector": k, "count": v} for k, v in sorted(sectors.items(), key=lambda item: item[1], reverse=True)],
        "by_data_status": [{"status": k, "count": v} for k, v in sorted(statuses.items(), key=lambda item: item[1], reverse=True)],
        "timeline": [{"month": k, "count": v} for k, v in sorted(timeline.items())],
        "groups": [
            {**g, "latest_seen": g["latest_seen"].isoformat() if g["latest_seen"] else None}
            for g in sorted(groups.values(), key=lambda item: item["victims"], reverse=True)
        ],
    }


@router.patch("/ransomware/victims/{victim_id}/seen")
async def mark_ransomware_victim_seen(
    victim_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkWebMention).where(
            and_(DarkWebMention.id == uuid.UUID(victim_id), _ransomware_filter())
        )
    )
    victim = result.scalar_one_or_none()
    if not victim:
        raise HTTPException(404, "Ransomware victim not found")
    if victim.analyst_seen_at is None:
        victim.analyst_seen_at = datetime.utcnow()
        await db.commit()
        await db.refresh(victim)
    return {"id": str(victim.id), "analyst_seen_at": victim.analyst_seen_at.isoformat() if victim.analyst_seen_at else None}


@router.get("/forum-mentions")
async def get_forum_mentions(
    forum_id: Optional[str] = None,
    severity: Optional[str] = None,
    keyword: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    sort_by: str = Query("feed_posted_at", regex="^(discovered_at|feed_posted_at)$"),
    year: Optional[int] = None,
    search_in: str = Query("all", regex="^(all|title)$"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(DarkWebMention).where(_forum_filter(days))
    if forum_id:
        query = query.where(DarkWebMention.source.ilike(f"%{forum_id}%"))
    if severity:
        query = query.where(DarkWebMention.severity == severity)
    if year:
        query = query.where(
            and_(
                DarkWebMention.feed_posted_at.isnot(None),
                func.extract("year", DarkWebMention.feed_posted_at) == year,
            )
        )
    if keyword:
        kw = keyword.strip()
        terms = [kw]
        kl = kw.lower()
        if kl == "srilanka":
            terms.append("sri lanka")
        elif kl == "sri lanka":
            terms.append("srilanka")
        elif kl in ("sl", "lk"):
            terms += ["sri lanka", "srilanka", ".lk"]
        conditions = [DarkWebMention.title.ilike(f"%{term}%") for term in terms]
        if search_in == "all":
            conditions = [
                condition
                for term in terms
                for condition in (
                    DarkWebMention.keyword_matched.ilike(f"%{term}%"),
                    DarkWebMention.title.ilike(f"%{term}%"),
                    DarkWebMention.snippet.ilike(f"%{term}%"),
                    DarkWebMention.victim_org.ilike(f"%{term}%"),
                    DarkWebMention.source_url.ilike(f"%{term}%"),
                )
            ]
        query = query.where(or_(*conditions))

    sort_col = DarkWebMention.discovered_at if sort_by == "discovered_at" else DarkWebMention.feed_posted_at
    result = await db.execute(
        query.order_by(desc(sort_col)).offset((page - 1) * limit).limit(limit)
    )
    mentions = result.scalars().all()

    total = (await db.execute(select(func.count(DarkWebMention.id)).where(_forum_filter()))).scalar()
    critical_high = (await db.execute(select(func.count(DarkWebMention.id)).where(and_(_forum_filter(), DarkWebMention.severity.in_(["CRITICAL", "HIGH"]))))).scalar()
    unreviewed = (await db.execute(select(func.count(DarkWebMention.id)).where(and_(_forum_filter(), DarkWebMention.is_reviewed == False)))).scalar()
    src_counts = await db.execute(
        select(DarkWebMention.source, func.count(DarkWebMention.id).label("c"))
        .where(_forum_filter(days))
        .group_by(DarkWebMention.source)
    )

    return {
        "mentions": [_serialize_mention(m) for m in mentions],
        "stats": {
            "total": total or 0,
            "critical_high": critical_high or 0,
            "unreviewed": unreviewed or 0,
            "by_source": {row[0]: row[1] for row in src_counts.all()},
        },
    }


@router.post("/forum-mentions/mark-all-viewed")
async def mark_all_forum_mentions_viewed(
    current_user=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkWebMention).where(and_(_forum_filter(), DarkWebMention.is_reviewed == False))
    )
    mentions = result.scalars().all()
    now = datetime.utcnow()
    username = str(getattr(current_user, "username", current_user.id))
    for m in mentions:
        m.is_reviewed = True
        m.triage_status = "reviewed"
        m.reviewed_by = username
        m.reviewed_at = now
    await db.commit()
    return {"marked": len(mentions)}


def _serialize_mention(mention: DarkWebMention):
    return {
        "id": str(mention.id),
        "title": mention.title,
        "snippet": mention.snippet,
        "source": mention.source,
        "source_url": mention.source_url,
        "severity": mention.severity,
        "keyword_matched": mention.keyword_matched,
        "threat_actor": mention.threat_actor,
        "victim_org": mention.victim_org,
        "is_reviewed": mention.is_reviewed,
        "is_false_positive": mention.is_false_positive,
        "triage_status": mention.triage_status,
        "analyst_notes": mention.analyst_notes,
        "discovered_at": mention.discovered_at.isoformat() if mention.discovered_at else None,
        "feed_posted_at": mention.feed_posted_at.isoformat() if mention.feed_posted_at else None,
        "raw_data": mention.raw_data or {},
    }


def _serialize_ransomware_victim(victim: DarkWebMention):
    posted_at = _ransomware_feed_posted_at(victim)
    return {
        "id": str(victim.id),
        "threat_actor": victim.threat_actor,
        "victim_org": victim.victim_org,
        "victim_country": victim.victim_country,
        "severity": victim.severity,
        "sector": _ransomware_sector(victim),
        "data_status": _ransomware_data_status(victim),
        "triage_status": victim.triage_status,
        "is_reviewed": victim.is_reviewed,
        "is_false_positive": victim.is_false_positive,
        "analyst_notes": victim.analyst_notes,
        "title": victim.title,
        "snippet": victim.snippet,
        "source_url": victim.source_url,
        "keyword_matched": victim.keyword_matched,
        "raw_data": victim.raw_data or {},
        "analyst_seen_at": victim.analyst_seen_at.isoformat() if victim.analyst_seen_at else None,
        "feed_posted_at": posted_at.isoformat() if posted_at else None,
        "posted_at": posted_at.isoformat() if posted_at else None,
        "collected_at": victim.discovered_at.isoformat() if victim.discovered_at else None,
        "ingested_at": victim.discovered_at.isoformat() if victim.discovered_at else None,
        "discovered_at": posted_at.isoformat() if posted_at else None,
        "published_at": victim.published_at.isoformat() if victim.published_at else None,
    }
