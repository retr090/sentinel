from celery import shared_task
from celery.utils.log import get_task_logger
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio

logger = get_task_logger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


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
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        otx_items = await fetch_otx_pulses()
        threatfox_items = await fetch_threatfox_iocs()
        urlhaus_items = await fetch_urlhaus_recent()

        # Get or create feed records
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
                description=pulse.get("description", "")[:500] if pulse.get("description") else None,
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
                title=f"Malicious URL: {url.get('url', '')[:80]}",
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


def _map_confidence_to_severity(confidence: int) -> str:
    if confidence >= 90:
        return "CRITICAL"
    if confidence >= 70:
        return "HIGH"
    if confidence >= 40:
        return "MEDIUM"
    return "LOW"
