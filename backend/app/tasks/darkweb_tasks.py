import asyncio
import hashlib
import uuid
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

logger = get_task_logger(__name__)

FORUM_KEYWORDS = [
    "sri lanka",
    "srilanka",
    "ceylon",
    ".lk",
    "gov.lk",
    "mil.lk",
    "colombo",
    "kandy",
    "jaffna",
    "bank of ceylon",
    "peoples bank",
    "mobitel",
]


def run_async(coro):
    return asyncio.run(coro)


def _make_session():
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return engine, session


def _stable_hash(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8", errors="ignore")).hexdigest()


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parts = urlsplit(url.strip())
        scheme = parts.scheme.lower() or "https"
        netloc = parts.netloc.lower()
        path = parts.path.rstrip("/")
        return urlunsplit((scheme, netloc, path, "", ""))
    except Exception:
        return url.strip().lower()


def _dedup_hash(source: str, source_url: str | None, title: str | None, snippet: str | None) -> str:
    return _stable_hash("|".join([source or "", source_url or "", title or "", (snippet or "")[:500]]))


def _ransomware_dedup_hash(threat_actor: str | None, victim_org: str | None) -> str:
    return _stable_hash(f"ransomware_live|{(threat_actor or '').strip().lower()}|{(victim_org or '').strip().lower()}")


def _severity_for_forum_result(title: str | None, snippet: str | None) -> tuple[str, str]:
    text = f"{title or ''} {snippet or ''}".lower()
    if any(term in text for term in ("database", "db dump", "credentials", "password", "stealer", "fullz")):
        return "HIGH", "Forum post appears to discuss leaked data or credentials"
    if any(term in text for term in ("leak", "breach", "dump", "access")):
        return "MEDIUM", "Forum post contains leak-related language"
    return "LOW", "Forum post matched monitored regional terms"


async def _save_mention(db, mention_data: dict) -> str:
    from app.models.darkweb import DarkWebAlert, DarkWebMention

    source = mention_data["source"]
    normalized_url = _normalize_url(mention_data.get("source_url"))
    if source == "ransomware_live" and mention_data.get("threat_actor") and mention_data.get("victim_org"):
        dedup_hash = mention_data.get("dedup_hash") or _ransomware_dedup_hash(
            mention_data.get("threat_actor"),
            mention_data.get("victim_org"),
        )
    else:
        dedup_hash = mention_data.get("dedup_hash") or _dedup_hash(
            source,
            normalized_url,
            mention_data.get("title"),
            mention_data.get("snippet"),
        )

    existing = (await db.execute(
        select(DarkWebMention).where(DarkWebMention.dedup_hash == dedup_hash)
    )).scalar_one_or_none()
    if existing:
        feed_posted_at = mention_data.get("feed_posted_at") or mention_data.get("published_at")
        if existing.feed_posted_at is None and feed_posted_at:
            existing.feed_posted_at = feed_posted_at
            await db.commit()
        return "existing"

    severity = mention_data.get("severity")
    severity_reason = mention_data.get("severity_reason")
    if not severity:
        severity, severity_reason = _severity_for_forum_result(
            mention_data.get("title"),
            mention_data.get("snippet"),
        )

    mention = DarkWebMention(
        id=uuid.uuid4(),
        keyword_matched=mention_data.get("keyword_matched") or "regional_match",
        source=source,
        source_url=mention_data.get("source_url"),
        normalized_source_url=normalized_url,
        dedup_hash=dedup_hash,
        content_hash=mention_data.get("content_hash") or _stable_hash(
            f"{mention_data.get('title', '')}\n{mention_data.get('snippet', '')}\n{mention_data.get('full_content', '')}"
        ),
        title=mention_data.get("title") or "Untitled",
        snippet=mention_data.get("snippet"),
        full_content=mention_data.get("full_content"),
        severity=severity,
        severity_reason=severity_reason,
        category=mention_data.get("category"),
        threat_actor=mention_data.get("threat_actor"),
        victim_org=mention_data.get("victim_org"),
        victim_country=mention_data.get("victim_country"),
        feed_posted_at=mention_data.get("feed_posted_at") or mention_data.get("published_at"),
        published_at=mention_data.get("published_at"),
        raw_data=mention_data.get("raw_data") or {},
        discovered_at=datetime.utcnow(),
        is_reviewed=False,
        is_false_positive=False,
        triage_status="new",
    )
    db.add(mention)

    if severity in ("CRITICAL", "HIGH"):
        title = (mention.title or "Intelligence finding")[:100]
        db.add(DarkWebAlert(
            id=uuid.uuid4(),
            mention_id=mention.id,
            severity=severity,
            title=f"Dark Web Intel: {title}",
            message=f"New {source} finding matched {mention.keyword_matched}",
            is_acknowledged=False,
            notification_sent=False,
            created_at=datetime.utcnow(),
        ))

    await db.commit()
    return "new"


async def _run_ransomware_scan() -> dict:
    from app.models.darkweb import DarkWebScan
    from app.services.darkweb.sources.ransomware_live import (
        fetch_victims_by_country,
        parse_victim,
    )

    engine, async_session = _make_session()
    try:
        async with async_session() as db:
            scan = DarkWebScan(
                id=uuid.uuid4(),
                scan_type="ransomware",
                source="ransomware_live",
                status="running",
                started_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            db.add(scan)
            await db.commit()

            try:
                total_found = 0
                new_mentions = 0

                victims = await fetch_victims_by_country("LK")
                scan.keywords_scanned = 0

                for victim in victims:
                    status = await _save_mention(db, parse_victim(victim, is_lk=True, keyword_matched="country:LK"))
                    total_found += 1
                    if status == "new":
                        new_mentions += 1

                scan.status = "completed"
                scan.mentions_found = total_found
                scan.new_mentions = new_mentions
                scan.completed_at = datetime.utcnow()
                scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()
                await db.commit()
                return {"found": total_found, "new": new_mentions}
            except Exception as exc:
                scan.status = "failed"
                scan.error_message = str(exc)
                scan.completed_at = datetime.utcnow()
                await db.commit()
                raise
    finally:
        await engine.dispose()


async def _run_historical_ransomware_scan() -> dict:
    from app.models.darkweb import DarkWebScan
    from app.services.darkweb.sources.ransomware_live import fetch_victims_by_country, parse_victim

    engine, async_session = _make_session()
    try:
        async with async_session() as db:
            scan = DarkWebScan(
                id=uuid.uuid4(),
                scan_type="ransomware_historical",
                source="ransomware_live",
                status="running",
                started_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            db.add(scan)
            await db.commit()

            try:
                victims = await fetch_victims_by_country("LK")
                new_mentions = 0
                for victim in victims:
                    status = await _save_mention(db, parse_victim(victim, is_lk=True, keyword_matched="country:LK"))
                    if status == "new":
                        new_mentions += 1

                scan.status = "completed"
                scan.keywords_scanned = 0
                scan.mentions_found = len(victims)
                scan.new_mentions = new_mentions
                scan.completed_at = datetime.utcnow()
                scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()
                await db.commit()
                return {"total": len(victims), "new": new_mentions}
            except Exception as exc:
                scan.status = "failed"
                scan.error_message = str(exc)
                scan.completed_at = datetime.utcnow()
                await db.commit()
                raise
    finally:
        await engine.dispose()


async def _run_surface_forum_scan() -> dict:
    from app.models.darkweb import DarkWebAlert, DarkWebScan
    from app.models.forum_credentials import ForumCredential
    from app.services.darkweb.ai_analyst import enrich_results
    from app.services.darkweb.forum_auth import ensure_valid_session
    from app.services.darkweb.sources.breached_st import run_full_scan

    engine, async_session = _make_session()
    try:
        async with async_session() as db:
            scan = DarkWebScan(
                id=uuid.uuid4(),
                scan_type="forums",
                source="all_forums",
                status="running",
                started_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            db.add(scan)
            await db.commit()

            try:
                active_forums = (await db.execute(
                    select(ForumCredential).where(ForumCredential.is_active == True)
                )).scalars().all()

                all_matches = []
                for forum in active_forums:
                    is_valid, auth_error = await ensure_valid_session(forum, db)
                    if not is_valid:
                        if any(word in auth_error.lower() for word in ("password", "failed", "decrypt")):
                            db.add(DarkWebAlert(
                                id=uuid.uuid4(),
                                mention_id=uuid.uuid4(),
                                severity="HIGH",
                                title=f"Forum auth failed: {forum.forum_name}",
                                message=auth_error,
                                is_acknowledged=False,
                                notification_sent=False,
                                created_at=datetime.utcnow(),
                            ))
                            await db.commit()
                        continue

                    software = (forum.forum_software or "mybb").lower()
                    if software == "xenforo" or "breached" in forum.forum_id.lower():
                        matches = await run_full_scan(cookies=forum.session_cookies, keywords=FORUM_KEYWORDS)
                        all_matches.extend([m for m in matches if not m.get("error")])

                    forum.last_used = datetime.utcnow()
                    await db.commit()

                if all_matches:
                    all_matches = await enrich_results(all_matches)

                new_count = 0
                for match in all_matches:
                    if await _save_mention(db, match) == "new":
                        new_count += 1

                scan.status = "completed"
                scan.keywords_scanned = len(FORUM_KEYWORDS)
                scan.mentions_found = len(all_matches)
                scan.new_mentions = new_count
                scan.completed_at = datetime.utcnow()
                scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()
                await db.commit()
                return {"found": len(all_matches), "new": new_count}
            except Exception as exc:
                scan.status = "failed"
                scan.error_message = str(exc)
                scan.completed_at = datetime.utcnow()
                await db.commit()
                raise
    finally:
        await engine.dispose()


@shared_task(name="app.tasks.darkweb_tasks.scan_ransomware_live", bind=True, max_retries=3, default_retry_delay=60, queue="darkweb")
def scan_ransomware_live(self):
    try:
        return run_async(_run_ransomware_scan())
    except Exception as exc:
        logger.error("scan_ransomware_live failed", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(name="app.tasks.darkweb_tasks.scan_ransomware_manual", bind=True, max_retries=1, queue="darkweb")
def scan_ransomware_manual(self):
    try:
        return run_async(_run_ransomware_scan())
    except Exception as exc:
        logger.error("scan_ransomware_manual failed", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(name="app.tasks.darkweb_tasks.scan_ransomware_historical", bind=True, max_retries=1, queue="darkweb")
def scan_ransomware_historical(self):
    try:
        return run_async(_run_historical_ransomware_scan())
    except Exception as exc:
        logger.error("scan_ransomware_historical failed", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(name="app.tasks.darkweb_tasks.scan_forums", bind=True, max_retries=2, default_retry_delay=300, queue="darkweb")
def scan_forums(self):
    try:
        return run_async(_run_surface_forum_scan())
    except Exception as exc:
        logger.error("scan_forums failed", exc_info=True)
        raise self.retry(exc=exc)
