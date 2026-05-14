from celery import shared_task
from celery.utils.log import get_task_logger
import asyncio
from datetime import datetime, timezone, timedelta

logger = get_task_logger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─────────────────────────────────────────────
# FEED FETCH (scheduled hourly)
# ─────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="feeds",
    name="app.tasks.threat_intel.fetch_all_feeds",
)
def fetch_all_feeds(self):
    try:
        run_async(_fetch_all_feeds_async())
    except Exception as exc:
        logger.error("fetch_all_feeds failed", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _fetch_all_feeds_async():
    from app.core.database import AsyncSessionLocal
    from app.models.threat_intel import ThreatFeed, FeedItem
    from app.services.threat_intel import fetch_otx_pulses, fetch_threatfox_iocs, fetch_urlhaus_recent
    from app.core.redis import publish_event
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        otx_items = await fetch_otx_pulses()
        threatfox_items = await fetch_threatfox_iocs()
        urlhaus_items = await fetch_urlhaus_recent()

        feed_map = {}
        for feed_name in ("AlienVault OTX", "ThreatFox", "URLhaus"):
            result = await db.execute(select(ThreatFeed).where(ThreatFeed.name == feed_name))
            feed = result.scalar_one_or_none()
            if not feed:
                feed = ThreatFeed(name=feed_name, feed_type=feed_name.lower().replace(" ", "_"))
                db.add(feed)
                await db.flush()
            feed_map[feed_name] = feed.id

        new_count = 0
        for pulse in otx_items[:50]:
            item = FeedItem(
                feed_id=feed_map["AlienVault OTX"],
                title=pulse.get("name", ""),
                description=(pulse.get("description", "") or "")[:500] or None,
                severity="MEDIUM",
                raw_data={k: v for k, v in pulse.items() if k in ("name", "tags", "tlp", "created")},
                published_at=datetime.now(timezone.utc),
            )
            db.add(item)
            new_count += 1

        for ioc in threatfox_items[:100]:
            item = FeedItem(
                feed_id=feed_map["ThreatFox"],
                title=ioc.get("threat_type_desc", "ThreatFox IOC"),
                ioc_value=ioc.get("ioc", ""),
                ioc_type=ioc.get("ioc_type", ""),
                severity=_map_confidence_to_severity(ioc.get("confidence_level", 50)),
                raw_data={k: v for k, v in ioc.items() if k in ("malware_alias", "threat_type", "reporter")},
                source_url=f"https://threatfox.abuse.ch/ioc/{ioc.get('id', '')}",
                published_at=datetime.now(timezone.utc),
            )
            db.add(item)
            new_count += 1

        for url in urlhaus_items[:50]:
            item = FeedItem(
                feed_id=feed_map["URLhaus"],
                title=f"Malicious URL: {(url.get('url', '') or '')[:80]}",
                ioc_value=url.get("url", ""),
                ioc_type="url",
                severity="HIGH" if url.get("threat") == "malware_download" else "MEDIUM",
                raw_data={k: v for k, v in url.items() if k in ("threat", "tags", "reporter")},
                source_url=url.get("urlhaus_reference", ""),
                published_at=datetime.now(timezone.utc),
            )
            db.add(item)
            new_count += 1

        await db.commit()
        logger.info("Threat feeds fetched", new_items=new_count)

        if new_count > 0:
            await publish_event("threat-intel", {"type": "feed_update", "new_items": new_count})


# ─────────────────────────────────────────────
# BULK IOC LOOKUP
# ─────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    queue="feeds",
    name="app.tasks.threat_intel.run_bulk_ioc_lookup",
)
def run_bulk_ioc_lookup(self, job_id: int, ioc_list: list, user_id: int):
    try:
        run_async(_run_bulk_async(job_id, ioc_list, user_id))
    except Exception as exc:
        logger.error("run_bulk_ioc_lookup failed", job_id=job_id, exc_info=True)
        run_async(_mark_job_failed(job_id))
        raise


async def _run_bulk_async(job_id: int, ioc_list: list, user_id: int):
    from app.core.database import AsyncSessionLocal
    from app.models.threat_intel import IOCBulkJob, IOC
    from app.services.threat_intel import detect_ioc_type, enrich_ioc, calculate_risk_score
    from sqlalchemy import select
    from sqlalchemy.orm.attributes import flag_modified

    async with AsyncSessionLocal() as db:
        job = (await db.execute(select(IOCBulkJob).where(IOCBulkJob.id == job_id))).scalar_one_or_none()
        if not job:
            logger.error("Bulk job not found", job_id=job_id)
            return

        job.status = "running"
        await db.commit()

        results = []
        for i, ioc_value in enumerate(ioc_list):
            ioc_value = ioc_value.strip()
            if not ioc_value:
                continue
            try:
                ioc_type = detect_ioc_type(ioc_value)
                enrichments = await enrich_ioc(ioc_value)
                risk_score, risk_level = calculate_risk_score(enrichments)

                existing = (await db.execute(
                    select(IOC).where(IOC.value == ioc_value)
                )).scalar_one_or_none()

                if existing:
                    existing.risk_score = risk_score
                    existing.risk_level = risk_level
                    existing.last_seen = datetime.now(timezone.utc)
                    existing.raw_data = enrichments
                    existing.sources = list(enrichments.keys())
                    ioc_id = existing.id
                else:
                    ioc = IOC(
                        value=ioc_value,
                        ioc_type=ioc_type,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        raw_data=enrichments,
                        sources=list(enrichments.keys()),
                        created_by=user_id,
                    )
                    db.add(ioc)
                    await db.flush()
                    ioc_id = ioc.id

                results = (job.results or []) + [{
                    "id": ioc_id,
                    "value": ioc_value,
                    "ioc_type": ioc_type,
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                }]
                job.processed = i + 1
                job.results = results
                flag_modified(job, 'results')
                await db.commit()

            except Exception as e:
                logger.warning("Failed to process IOC in bulk job", ioc=ioc_value, error=str(e))
                results = (job.results or []) + [{"value": ioc_value, "error": str(e)}]
                job.processed = i + 1
                job.results = results
                flag_modified(job, 'results')
                await db.commit()

        job.status = "completed"
        await db.commit()
        logger.info("Bulk IOC lookup completed", job_id=job_id, total=len(results))


async def _mark_job_failed(job_id: int):
    from app.core.database import AsyncSessionLocal
    from app.models.threat_intel import IOCBulkJob
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        job = (await db.execute(select(IOCBulkJob).where(IOCBulkJob.id == job_id))).scalar_one_or_none()
        if job:
            job.status = "failed"
            await db.commit()


# ─────────────────────────────────────────────
# STALE IOC REFRESH (scheduled daily)
# ─────────────────────────────────────────────

@shared_task(
    queue="feeds",
    name="app.tasks.threat_intel.refresh_stale_iocs",
)
def refresh_stale_iocs():
    run_async(_refresh_stale_async())


async def _refresh_stale_async():
    from app.core.database import AsyncSessionLocal
    from app.models.threat_intel import IOC
    from app.services.threat_intel import enrich_ioc, calculate_risk_score
    from sqlalchemy import select

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(IOC)
            .where(IOC.last_seen < cutoff, IOC.is_archived == False)
            .limit(100)
        )
        stale = result.scalars().all()

        refreshed = 0
        for ioc in stale:
            try:
                enrichments = await enrich_ioc(ioc.value)
                risk_score, risk_level = calculate_risk_score(enrichments)
                ioc.risk_score = risk_score
                ioc.risk_level = risk_level
                ioc.raw_data = enrichments
                ioc.sources = list(enrichments.keys())
                ioc.last_seen = datetime.now(timezone.utc)
                refreshed += 1
            except Exception as e:
                logger.warning("Failed to refresh IOC", ioc=ioc.value, error=str(e))

        await db.commit()
        logger.info("Stale IOC refresh complete", refreshed=refreshed)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _map_confidence_to_severity(confidence: int) -> str:
    if confidence >= 90:
        return "CRITICAL"
    if confidence >= 70:
        return "HIGH"
    if confidence >= 40:
        return "MEDIUM"
    return "LOW"
