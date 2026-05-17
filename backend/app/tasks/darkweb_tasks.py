import asyncio
import uuid
from datetime import datetime
from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select, or_, and_

logger = get_task_logger(__name__)


def run_async(coro):
    # asyncio.run() creates a fresh event loop per call — avoids "Future attached
    # to a different loop" errors that occur when forked Celery workers reuse a
    # pooled connection tied to the parent process's event loop.
    return asyncio.run(coro)


def _make_session():
    """Create a fresh NullPool engine + session for each Celery task invocation."""
    from sqlalchemy.pool import NullPool
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    Session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return engine, Session


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_active_keywords(db) -> list:
    """Return all active keyword strings + their aliases."""
    from app.models.darkweb import DarkWebKeyword

    result = await db.execute(
        select(DarkWebKeyword).where(DarkWebKeyword.is_active == True)
    )
    terms = []
    for kw in result.scalars().all():
        terms.append(kw.keyword)
        if kw.aliases:
            terms.extend(kw.aliases)
    return list(set(terms))


async def _get_priority_keywords(db) -> list:
    """Return HIGH/CRITICAL priority keyword strings + aliases from the watchlist."""
    from app.models.darkweb import DarkWebKeyword

    result = await db.execute(
        select(DarkWebKeyword).where(
            DarkWebKeyword.is_active == True,
            DarkWebKeyword.priority.in_(["CRITICAL", "HIGH"]),
        )
    )
    terms = []
    for kw in result.scalars().all():
        terms.append(kw.keyword)
        if kw.aliases:
            terms.extend(kw.aliases[:3])
    return list(set(terms))


async def _save_mention(db, mention_data: dict, scan_id=None) -> str:
    """Save an intelligence mention. Returns 'new' or 'existing'."""
    from app.models.darkweb import DarkWebMention, DarkWebAlert

    source_url = mention_data.get("source_url")
    dedup_conditions = [
        and_(
            DarkWebMention.title == mention_data["title"],
            DarkWebMention.source == mention_data["source"],
        )
    ]
    if source_url:
        dedup_conditions.append(
            and_(
                DarkWebMention.source_url == source_url,
                DarkWebMention.source == mention_data["source"],
            )
        )
    existing = await db.execute(
        select(DarkWebMention).where(or_(*dedup_conditions))
    )
    if existing.scalar_one_or_none():
        return "existing"

    # Update keyword hit_count + last_hit
    from app.models.darkweb import DarkWebKeyword
    kw_str = mention_data.get("keyword_matched", "")
    if kw_str:
        kw_rows = await db.execute(
            select(DarkWebKeyword).where(
                DarkWebKeyword.keyword == kw_str,
                DarkWebKeyword.is_active == True,
            )
        )
        kw_row = kw_rows.scalar_one_or_none()
        if kw_row:
            kw_row.hit_count = (kw_row.hit_count or 0) + 1
            post_date = mention_data.get("published_at")
            # Keep last_hit as the most recent post date seen for this keyword
            if post_date:
                if not kw_row.last_hit or post_date > kw_row.last_hit:
                    kw_row.last_hit = post_date
            elif not kw_row.last_hit:
                kw_row.last_hit = datetime.utcnow()

    mention = DarkWebMention(
        id=uuid.uuid4(),
        keyword_matched=mention_data["keyword_matched"],
        source=mention_data["source"],
        source_url=mention_data.get("source_url"),
        title=mention_data["title"],
        snippet=mention_data.get("snippet"),
        full_content=mention_data.get("full_content"),
        severity=mention_data["severity"],
        category=mention_data.get("category"),
        threat_actor=mention_data.get("threat_actor"),
        victim_org=mention_data.get("victim_org"),
        victim_country=mention_data.get("victim_country"),
        published_at=mention_data.get("published_at"),
        raw_data=mention_data.get("raw_data", {}),
        discovered_at=datetime.utcnow(),
        is_reviewed=False,
        is_false_positive=False,
    )
    db.add(mention)

    if mention_data["severity"] in ("CRITICAL", "HIGH"):
        category = mention_data.get("category", "intelligence")
        source = mention_data.get("source", "unknown")
        keyword = mention_data["keyword_matched"]
        title_snippet = mention_data["title"][:100]

        if mention_data.get("threat_actor") and mention_data.get("victim_org"):
            msg = (
                f"Ransomware group {mention_data['threat_actor']} has targeted "
                f"{mention_data['victim_org']}. Keyword: {keyword}"
            )
        else:
            msg = (
                f"New {category} alert from {source}. "
                f"Keyword matched: {keyword}. Title: {title_snippet}"
            )

        alert = DarkWebAlert(
            id=uuid.uuid4(),
            mention_id=mention.id,
            severity=mention_data["severity"],
            title=f"Dark Web: {title_snippet}",
            message=msg,
            is_acknowledged=False,
            notification_sent=False,
            created_at=datetime.utcnow(),
        )
        db.add(alert)

    await db.commit()
    return "new"


# ── Phase 2: Ransomware.live ───────────────────────────────────────────────────

async def _run_ransomware_scan() -> dict:
    from app.models.darkweb import DarkWebScan
    from app.services.darkweb.sources.ransomware_live import (
        fetch_recent_victims,
        fetch_victims_by_country,
        is_sri_lanka_related,
        parse_victim,
    )

    engine, AsyncSessionLocal = _make_session()
    try:
        async with AsyncSessionLocal() as db:
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

                logger.info("Fetching LK victims from ransomware.live...")
                lk_victims = await fetch_victims_by_country("LK")
                logger.info(f"Got {len(lk_victims)} LK victims")

                for victim in lk_victims:
                    status = await _save_mention(
                        db,
                        parse_victim(victim, is_lk=True, keyword_matched="country:LK"),
                    )
                    total_found += 1
                    if status == "new":
                        new_mentions += 1

                logger.info("Fetching recent global victims...")
                recent = await fetch_recent_victims(days=7)
                logger.info(f"Got {len(recent)} recent victims globally")

                scan.keywords_scanned = len(recent)

                for victim in recent:
                    is_lk, keyword = is_sri_lanka_related(victim)
                    if is_lk:
                        status = await _save_mention(
                            db,
                            parse_victim(victim, is_lk=True, keyword_matched=keyword),
                        )
                        total_found += 1
                        if status == "new":
                            new_mentions += 1

                scan.status = "completed"
                scan.mentions_found = total_found
                scan.new_mentions = new_mentions
                scan.completed_at = datetime.utcnow()
                scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()
                await db.commit()

                logger.info(f"Ransomware scan complete: {total_found} LK-related, {new_mentions} new")
                return {"found": total_found, "new": new_mentions}

            except Exception as e:
                scan.status = "failed"
                scan.error_message = str(e)
                scan.completed_at = datetime.utcnow()
                await db.commit()
                logger.error(f"Ransomware scan failed: {e}", exc_info=True)
                raise
    finally:
        await engine.dispose()


# ── Historical Ransomware Scan ────────────────────────────────────────────────

async def _run_historical_ransomware_scan() -> dict:
    """Scan all historical per-year victim data from ransomware.live for SL hits."""
    from app.models.darkweb import DarkWebScan
    from app.services.darkweb.sources.ransomware_live import fetch_all_historical_lk, parse_victim

    engine, AsyncSessionLocal = _make_session()
    try:
        async with AsyncSessionLocal() as db:
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
                logger.info("Starting historical SL ransomware scan...")
                all_victims = await fetch_all_historical_lk()
                logger.info(f"Historical fetch complete: {len(all_victims)} SL victims found")

                total_found = 0
                new_mentions = 0
                for victim in all_victims:
                    keyword = victim.get("_match_type", "historical_scan")
                    status = await _save_mention(
                        db,
                        parse_victim(victim, is_lk=True, keyword_matched=keyword),
                    )
                    total_found += 1
                    if status == "new":
                        new_mentions += 1

                scan.status = "completed"
                scan.keywords_scanned = total_found
                scan.mentions_found = total_found
                scan.new_mentions = new_mentions
                scan.completed_at = datetime.utcnow()
                scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()
                await db.commit()

                logger.info(f"Historical scan done: {total_found} total, {new_mentions} new")
                return {"total": total_found, "new": new_mentions}

            except Exception as e:
                scan.status = "failed"
                scan.error_message = str(e)
                scan.completed_at = datetime.utcnow()
                await db.commit()
                logger.error(f"Historical ransomware scan failed: {e}", exc_info=True)
                raise
    finally:
        await engine.dispose()


# ── Phase 3: RSS Feeds ────────────────────────────────────────────────────────

async def _run_rss_scan() -> dict:
    from app.models.darkweb import DarkWebScan
    from app.services.darkweb.sources.rss_feeds import scan_all_feeds

    engine, AsyncSessionLocal = _make_session()
    try:
        async with AsyncSessionLocal() as db:
            scan = DarkWebScan(
                id=uuid.uuid4(),
                scan_type="rss",
                source="rss_feeds",
                status="running",
                started_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            db.add(scan)
            await db.commit()

            try:
                keywords = await _get_active_keywords(db)
                logger.info(f"RSS scan: {len(keywords)} keywords")

                matches = await scan_all_feeds(keywords)
                logger.info(f"RSS scan found {len(matches)} matches")

                new_count = 0
                for match in matches:
                    result = await _save_mention(db, match)
                    if result == "new":
                        new_count += 1

                scan.status = "completed"
                scan.keywords_scanned = len(keywords)
                scan.mentions_found = len(matches)
                scan.new_mentions = new_count
                scan.completed_at = datetime.utcnow()
                scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()
                await db.commit()

                logger.info(f"RSS scan complete: {len(matches)} found, {new_count} new")
                return {"found": len(matches), "new": new_count}

            except Exception as e:
                scan.status = "failed"
                scan.error_message = str(e)
                scan.completed_at = datetime.utcnow()
                await db.commit()
                logger.error(f"RSS scan failed: {e}", exc_info=True)
                raise
    finally:
        await engine.dispose()


# ── Phase 3: Paste Sites ──────────────────────────────────────────────────────

async def _run_paste_scan() -> dict:
    from app.models.darkweb import DarkWebScan, DarkWebKeyword
    from app.services.darkweb.sources.paste_monitor import check_recent_pastes

    engine, AsyncSessionLocal = _make_session()
    try:
        async with AsyncSessionLocal() as db:
            scan = DarkWebScan(
                id=uuid.uuid4(),
                scan_type="paste",
                source="paste_sites",
                status="running",
                started_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            db.add(scan)
            await db.commit()

            try:
                # Only use CRITICAL/HIGH priority keywords to limit request volume
                result = await db.execute(
                    select(DarkWebKeyword).where(
                        DarkWebKeyword.is_active == True,
                        DarkWebKeyword.priority.in_(["CRITICAL", "HIGH"]),
                    )
                )
                priority_terms = []
                for kw in result.scalars().all():
                    priority_terms.append(kw.keyword)
                    if kw.aliases:
                        priority_terms.extend(kw.aliases[:2])

                priority_terms = priority_terms[:20]
                logger.info(f"Paste scan: {len(priority_terms)} priority keywords")

                matches = await check_recent_pastes(priority_terms)
                logger.info(f"Paste scan found {len(matches)} matches")

                new_count = 0
                for match in matches:
                    match.setdefault("severity", "MEDIUM")
                    match.setdefault("category", "paste_leak")
                    result = await _save_mention(db, match)
                    if result == "new":
                        new_count += 1

                scan.status = "completed"
                scan.keywords_scanned = len(priority_terms)
                scan.mentions_found = len(matches)
                scan.new_mentions = new_count
                scan.completed_at = datetime.utcnow()
                scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()
                await db.commit()

                logger.info(f"Paste scan complete: {len(matches)} found, {new_count} new")
                return {"found": len(matches), "new": new_count}

            except Exception as e:
                scan.status = "failed"
                scan.error_message = str(e)
                scan.completed_at = datetime.utcnow()
                await db.commit()
                logger.error(f"Paste scan failed: {e}", exc_info=True)
                raise
    finally:
        await engine.dispose()


# ── Phase 3: Dark Web Search (Ahmia + DarkSearch) ────────────────────────────

async def _run_dark_web_search_scan() -> dict:
    from app.models.darkweb import DarkWebScan, DarkWebKeyword
    from app.services.darkweb.sources import ahmia, darksearch

    engine, AsyncSessionLocal = _make_session()
    try:
        async with AsyncSessionLocal() as db:
            scan = DarkWebScan(
                id=uuid.uuid4(),
                scan_type="dark_web_search",
                source="ahmia_darksearch",
                status="running",
                started_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            db.add(scan)
            await db.commit()

            try:
                result = await db.execute(
                    select(DarkWebKeyword).where(
                        DarkWebKeyword.is_active == True,
                        DarkWebKeyword.priority.in_(["CRITICAL", "HIGH"]),
                    ).limit(15)
                )
                keywords = [kw.keyword for kw in result.scalars().all()]
                logger.info(f"Dark web search: {len(keywords)} keywords")

                all_matches = []

                # Ahmia — search top 10 keywords
                ahmia_results = await ahmia.search_multiple_keywords(
                    keywords[:10], limit_per_keyword=5
                )
                for r in ahmia_results:
                    if not r.get("error"):
                        all_matches.append({
                            "keyword_matched": r.get("keyword_matched", ""),
                            "source": "ahmia",
                            "source_url": r.get("url", ""),
                            "title": r.get("title", "No title"),
                            "snippet": r.get("snippet", ""),
                            "severity": "MEDIUM",
                            "category": "dark_web_search",
                            "raw_data": r,
                        })

                # DarkSearch — search top 5 keywords
                ds_tasks = [darksearch.search(kw) for kw in keywords[:5]]
                ds_results = await asyncio.gather(*ds_tasks, return_exceptions=True)
                for kw, results in zip(keywords[:5], ds_results):
                    if isinstance(results, Exception):
                        continue
                    for r in results:
                        if not r.get("error"):
                            all_matches.append({
                                "keyword_matched": kw,
                                "source": "darksearch",
                                "source_url": r.get("url", ""),
                                "title": r.get("title", "No title"),
                                "snippet": r.get("snippet", ""),
                                "severity": "MEDIUM",
                                "category": "dark_web_search",
                                "raw_data": r,
                            })

                logger.info(f"Dark web search found {len(all_matches)} matches")

                new_count = 0
                for match in all_matches:
                    res = await _save_mention(db, match)
                    if res == "new":
                        new_count += 1

                scan.status = "completed"
                scan.keywords_scanned = len(keywords)
                scan.mentions_found = len(all_matches)
                scan.new_mentions = new_count
                scan.completed_at = datetime.utcnow()
                scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()
                await db.commit()

                logger.info(f"Dark web search complete: {len(all_matches)} found, {new_count} new")
                return {"found": len(all_matches), "new": new_count}

            except Exception as e:
                scan.status = "failed"
                scan.error_message = str(e)
                scan.completed_at = datetime.utcnow()
                await db.commit()
                logger.error(f"Dark web search failed: {e}", exc_info=True)
                raise
    finally:
        await engine.dispose()


# ── Celery Tasks ──────────────────────────────────────────────────────────────

@shared_task(
    name="app.tasks.darkweb_tasks.scan_ransomware_live",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="darkweb",
)
def scan_ransomware_live(self):
    """Celery beat task: scan Ransomware.live every 15 minutes."""
    try:
        return run_async(_run_ransomware_scan())
    except Exception as exc:
        logger.error("scan_ransomware_live failed", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    name="app.tasks.darkweb_tasks.scan_ransomware_manual",
    bind=True,
    max_retries=1,
    queue="darkweb",
)
def scan_ransomware_manual(self):
    """Manual trigger: immediate ransomware scan."""
    try:
        return run_async(_run_ransomware_scan())
    except Exception as exc:
        logger.error("scan_ransomware_manual failed", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    name="app.tasks.darkweb_tasks.scan_rss_feeds",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    queue="darkweb",
)
def scan_rss_feeds(self):
    """Scan all RSS intelligence feeds for keyword matches."""
    try:
        return run_async(_run_rss_scan())
    except Exception as exc:
        logger.error("scan_rss_feeds failed", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    name="app.tasks.darkweb_tasks.scan_paste_sites",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    queue="darkweb",
)
def scan_paste_sites(self):
    """Scan paste sites for high-priority keyword matches."""
    try:
        return run_async(_run_paste_scan())
    except Exception as exc:
        logger.error("scan_paste_sites failed", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    name="app.tasks.darkweb_tasks.scan_dark_web_search",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    queue="darkweb",
)
def scan_dark_web_search(self):
    """Search Ahmia and DarkSearch for CRITICAL/HIGH priority keywords."""
    try:
        return run_async(_run_dark_web_search_scan())
    except Exception as exc:
        logger.error("scan_dark_web_search failed", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    name="app.tasks.darkweb_tasks.scan_ransomware_historical",
    bind=True,
    max_retries=1,
    queue="darkweb",
)
def scan_ransomware_historical(self):
    """One-time deep historical scan: all years on ransomware.live filtered for SL."""
    try:
        return run_async(_run_historical_ransomware_scan())
    except Exception as exc:
        logger.error("scan_ransomware_historical failed", exc_info=True)
        raise self.retry(exc=exc)


# ── Phase 5: Forum Scan (Breached.st + others) ────────────────────────────────

async def _run_surface_forum_scan() -> dict:
    from app.models.darkweb import DarkWebScan, DarkWebAlert
    from app.models.forum_credentials import ForumCredential
    from app.services.darkweb.sources.breached_st import run_full_scan
    from app.services.darkweb.forum_auth import ensure_valid_session

    engine, AsyncSessionLocal = _make_session()
    try:
        async with AsyncSessionLocal() as db:
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
                scan_keywords = await _get_priority_keywords(db)
                if not scan_keywords:
                    logger.info("No active keywords configured — skipping forum scan")
                    scan.status = "completed"
                    scan.keywords_scanned = 0
                    scan.mentions_found = 0
                    scan.new_mentions = 0
                    scan.completed_at = datetime.utcnow()
                    scan.duration_seconds = 0
                    await db.commit()
                    return {"found": 0, "new": 0, "skipped": "no keywords"}

                logger.info(f"Forum scan: {len(scan_keywords)} keywords from DB watchlist")

                all_matches = []

                # Fetch all active forums (not just breached_st)
                result = await db.execute(
                    select(ForumCredential).where(ForumCredential.is_active == True)
                )
                active_forums = result.scalars().all()

                if not active_forums:
                    logger.info("No active forum credentials configured — skipping forum scan")
                else:
                    for forum in active_forums:
                        logger.info(f"Processing forum: {forum.forum_name} ({forum.forum_software})")
                        is_valid, auth_error = await ensure_valid_session(forum, db)

                        if not is_valid:
                            logger.warning(f"{forum.forum_name} unavailable: {auth_error}")
                            if any(w in auth_error.lower() for w in ("password", "failed", "decrypt")):
                                alert = DarkWebAlert(
                                    id=uuid.uuid4(),
                                    mention_id=uuid.uuid4(),
                                    severity="HIGH",
                                    title=f"Forum auth failed: {forum.forum_name}",
                                    message=auth_error,
                                    is_acknowledged=False,
                                    notification_sent=False,
                                    created_at=datetime.utcnow(),
                                )
                                db.add(alert)
                                await db.commit()
                            continue

                        # Route to the right scanner based on forum software / id
                        software = (forum.forum_software or "mybb").lower()
                        if software == "xenforo" or "breached" in forum.forum_id.lower():
                            logger.info(f"Running XenForo/Breached.st scan on {forum.forum_name}...")
                            matches = await run_full_scan(
                                cookies=forum.session_cookies,
                                keywords=scan_keywords,
                            )
                            all_matches.extend([m for m in matches if not m.get("error")])
                        else:
                            logger.info(f"No scanner implemented for {software} ({forum.forum_name}) — skipping")
                            continue

                        forum.last_used = datetime.utcnow()
                        await db.commit()

                # AI enrichment — filters non-breaches and extracts structured data.
                # No-op if GROQ_API_KEY is not configured.
                if all_matches:
                    from app.services.darkweb.ai_analyst import enrich_results
                    all_matches = await enrich_results(all_matches)

                new_count = 0
                for match in all_matches:
                    res = await _save_mention(db, match)
                    if res == "new":
                        new_count += 1

                scan.status = "completed"
                scan.keywords_scanned = len(scan_keywords)
                scan.mentions_found = len(all_matches)
                scan.new_mentions = new_count
                scan.completed_at = datetime.utcnow()
                scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()
                await db.commit()

                logger.info(f"Forum scan complete: {len(all_matches)} found, {new_count} new")
                return {"found": len(all_matches), "new": new_count}

            except Exception as e:
                scan.status = "failed"
                scan.error_message = str(e)
                scan.completed_at = datetime.utcnow()
                await db.commit()
                logger.error(f"Forum scan failed: {e}", exc_info=True)
                raise
    finally:
        await engine.dispose()


@shared_task(
    name="app.tasks.darkweb_tasks.scan_forums",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    queue="darkweb",
)
def scan_forums(self):
    """Scan authenticated forums (Breached.st etc.) for keyword matches."""
    try:
        return run_async(_run_surface_forum_scan())
    except Exception as exc:
        logger.error("scan_forums failed", exc_info=True)
        raise self.retry(exc=exc)
