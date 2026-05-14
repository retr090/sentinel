from celery import shared_task
from celery.utils.log import get_task_logger
import asyncio

logger = get_task_logger(__name__)

DEFAULT_RSS_SOURCES = [
    {"name": "Ada Derana", "url": "https://www.adaderana.lk/rss.php", "category": "regional", "language": "en"},
    {"name": "Daily FT", "url": "https://www.ft.lk/rss", "category": "regional", "language": "en"},
    {"name": "Colombo Gazette", "url": "https://colombogazette.com/feed/", "category": "regional", "language": "en"},
    {"name": "BBC Sinhala", "url": "https://feeds.bbci.co.uk/sinhala/rss.xml", "category": "regional", "language": "si"},
    {"name": "SecurityWeek", "url": "https://feeds.feedburner.com/securityweek", "category": "cyber", "language": "en"},
    {"name": "The Diplomat", "url": "https://thediplomat.com/feed/", "category": "military", "language": "en"},
    {"name": "VOA English", "url": "https://www.voanews.com/api/zmpkrqqvyi", "category": "general", "language": "en"},
]


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
    name="app.tasks.news.fetch_all_news",
)
def fetch_all_news(self):
    try:
        run_async(_fetch_all_news_async())
    except Exception as exc:
        logger.error("fetch_all_news failed", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _fetch_all_news_async():
    import feedparser
    import httpx
    from app.core.database import AsyncSessionLocal
    from app.models.news import NewsSource, NewsArticle
    from sqlalchemy import select
    from datetime import datetime, timezone
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    sia = SentimentIntensityAnalyzer()

    async with AsyncSessionLocal() as db:
        # Ensure default sources exist
        for src_data in DEFAULT_RSS_SOURCES:
            result = await db.execute(select(NewsSource).where(NewsSource.url == src_data["url"]))
            if not result.scalar_one_or_none():
                db.add(NewsSource(**src_data, source_type="rss"))

        await db.flush()

        result = await db.execute(select(NewsSource).where(NewsSource.is_active == True, NewsSource.source_type == "rss"))
        sources = result.scalars().all()

        new_count = 0
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            for source in sources:
                try:
                    r = await client.get(source.url, follow_redirects=True)
                    if r.status_code != 200:
                        continue

                    feed = feedparser.parse(r.text)
                    for entry in feed.entries[:20]:
                        url = entry.get("link", "")
                        if not url:
                            continue

                        existing = (await db.execute(select(NewsArticle).where(NewsArticle.url == url))).scalar_one_or_none()
                        if existing:
                            continue

                        title = entry.get("title", "")
                        summary = entry.get("summary", "")[:1000] if entry.get("summary") else ""

                        sentiment = sia.polarity_scores(title + " " + summary)
                        compound = sentiment["compound"]
                        label = "positive" if compound >= 0.05 else "negative" if compound <= -0.05 else "neutral"

                        published = None
                        if entry.get("published_parsed"):
                            import time
                            published = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)

                        article = NewsArticle(
                            source_id=source.id,
                            title=title,
                            url=url,
                            content_snippet=summary,
                            author=entry.get("author"),
                            category=source.category,
                            sentiment_score=compound,
                            sentiment_label=label,
                            language=source.language,
                            published_at=published,
                        )
                        db.add(article)
                        new_count += 1

                    source.last_fetched = datetime.now(timezone.utc)
                except Exception as e:
                    logger.warning("RSS fetch failed", source=source.name, error=str(e))

        await db.commit()
        logger.info("News fetch complete", new_articles=new_count)
