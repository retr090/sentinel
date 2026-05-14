from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.threat_intel import IOC, FeedItem
from app.models.dark_web import DarkWebMention
from app.models.news import NewsArticle
from app.models.alerts import Alert
from app.models.cyber_surface import MonitoredAsset, AssetVulnerability
from app.models.geoint import GeoItem
from app.models.socmint import SocialPost
from app.models.profile import Profile

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)

    async def count(model, *conditions):
        q = select(func.count()).select_from(model)
        for c in conditions:
            q = q.where(c)
        return (await db.execute(q)).scalar() or 0

    # Alert counts by severity (open)
    alert_counts = {}
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        alert_counts[sev] = await count(Alert, Alert.severity == sev, Alert.status == "open", Alert.is_archived == False)

    # Module stats
    iocs_24h = await count(IOC, IOC.created_at >= since_24h)
    dark_web_24h = await count(DarkWebMention, DarkWebMention.found_at >= since_24h)
    news_24h = await count(NewsArticle, NewsArticle.created_at >= since_24h)
    social_24h = await count(SocialPost, SocialPost.created_at >= since_24h)
    assets_monitored = await count(MonitoredAsset, MonitoredAsset.is_active == True)
    critical_vulns = await count(AssetVulnerability, AssetVulnerability.severity == "CRITICAL", AssetVulnerability.is_resolved == False)
    profiles_total = await count(Profile, Profile.is_archived == False)

    # Recent alerts
    recent_alerts_q = await db.execute(
        select(Alert)
        .where(Alert.is_archived == False)
        .order_by(Alert.triggered_at.desc())
        .limit(20)
    )
    recent_alerts = recent_alerts_q.scalars().all()

    # News volume last 7 days (daily)
    news_timeline_q = await db.execute(
        select(
            func.date_trunc('day', NewsArticle.published_at).label("date"),
            func.count().label("count"),
        )
        .where(NewsArticle.published_at >= since_7d, NewsArticle.is_archived == False)
        .group_by(func.date_trunc('day', NewsArticle.published_at))
        .order_by("date")
    )
    news_timeline = [{"date": r.date.isoformat() if r.date else None, "count": r.count} for r in news_timeline_q.all()]

    # Recent geo items
    recent_geo_q = await db.execute(
        select(GeoItem)
        .where(GeoItem.is_archived == False)
        .order_by(GeoItem.created_at.desc())
        .limit(10)
    )
    recent_geo = recent_geo_q.scalars().all()

    return {
        "alerts": {
            "by_severity": alert_counts,
            "total_open": sum(alert_counts.values()),
        },
        "modules": {
            "threat_intel": {"iocs_24h": iocs_24h},
            "dark_web": {"mentions_24h": dark_web_24h},
            "news": {"articles_24h": news_24h},
            "socmint": {"posts_24h": social_24h},
            "cyber_surface": {"assets": assets_monitored, "critical_vulns": critical_vulns},
            "profiles": {"total": profiles_total},
        },
        "news_timeline": news_timeline,
        "recent_alerts": [
            {
                "id": a.id,
                "title": a.title,
                "severity": a.severity,
                "module": a.module,
                "status": a.status,
                "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            }
            for a in recent_alerts
        ],
        "recent_geo": [
            {
                "id": g.id,
                "title": g.title,
                "latitude": g.latitude,
                "longitude": g.longitude,
                "item_type": g.item_type,
                "severity": g.severity,
            }
            for g in recent_geo
        ],
    }


@router.get("/search")
async def global_search(
    q: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Route a search query to the most relevant module."""
    import re
    q = q.strip()
    if not q:
        return {"type": "empty", "redirect": "/"}

    ip_re = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    hash_re = re.compile(r"^[a-fA-F0-9]{32,64}$")
    url_re = re.compile(r"^https?://")
    email_re = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
    domain_re = re.compile(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    if ip_re.match(q):
        return {"type": "ip", "redirect": f"/threat-intel?search={q}", "query": q}
    if hash_re.match(q):
        return {"type": "hash", "redirect": f"/threat-intel?search={q}", "query": q}
    if url_re.match(q):
        return {"type": "url", "redirect": f"/threat-intel?search={q}", "query": q}
    if email_re.match(q):
        return {"type": "email", "redirect": f"/profiles?search={q}", "query": q}
    if domain_re.match(q):
        return {"type": "domain", "redirect": f"/profiles?search={q}", "query": q}

    return {"type": "keyword", "redirect": f"/news?keyword={q}", "query": q}
