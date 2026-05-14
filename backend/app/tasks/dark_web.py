from celery import shared_task
from celery.utils.log import get_task_logger
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
    default_retry_delay=120,
    queue="feeds",
    name="app.tasks.dark_web.scan_watchlist",
)
def scan_watchlist(self):
    try:
        run_async(_scan_watchlist_async())
    except Exception as exc:
        logger.error("scan_watchlist failed", exc_info=True)
        raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))


async def _scan_watchlist_async():
    from app.core.database import AsyncSessionLocal
    from app.models.dark_web import WatchlistKeyword, DarkWebMention
    from app.services.dark_web import scan_keyword_dark_web
    from app.core.redis import publish_event
    from sqlalchemy import select
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(WatchlistKeyword).where(WatchlistKeyword.is_active == True))
        keywords = result.scalars().all()

        new_findings = 0
        for kw in keywords:
            findings = await scan_keyword_dark_web(kw.keyword)
            for finding in findings:
                mention = DarkWebMention(
                    keyword_id=kw.id,
                    keyword=kw.keyword,
                    source=finding.get("source"),
                    source_url=finding.get("source_url"),
                    title=finding.get("title"),
                    snippet=finding.get("snippet", "")[:1000] if finding.get("snippet") else None,
                    severity=kw.severity,
                    found_at=datetime.now(timezone.utc),
                )
                db.add(mention)
                new_findings += 1

            kw.last_scanned = datetime.now(timezone.utc)

        await db.commit()
        logger.info("Dark web scan complete", new_findings=new_findings)

        if new_findings > 0:
            await publish_event("dark-web", {"type": "new_mentions", "count": new_findings})
