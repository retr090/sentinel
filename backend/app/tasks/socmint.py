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
    default_retry_delay=60,
    queue="feeds",
    name="app.tasks.socmint.scan_all_keywords",
)
def scan_all_keywords(self):
    try:
        run_async(_scan_all_async())
    except Exception as exc:
        logger.error("scan_all_keywords failed", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _scan_all_async():
    import httpx
    from app.core.database import AsyncSessionLocal
    from app.models.socmint import SocialKeyword, SocialPost
    from sqlalchemy import select
    from datetime import datetime, timezone
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    sia = SentimentIntensityAnalyzer()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SocialKeyword).where(SocialKeyword.is_active == True))
        keywords = result.scalars().all()

        new_posts = 0
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0), headers={"User-Agent": "bot"}) as client:
            for kw in keywords:
                platforms = kw.platforms or ["reddit"]

                if "reddit" in platforms:
                    reddit_posts = await _fetch_reddit(client, kw.keyword)
                    for post in reddit_posts:
                        text = post.get("title", "") + " " + post.get("selftext", "")
                        sentiment = sia.polarity_scores(text)
                        compound = sentiment["compound"]
                        label = "positive" if compound >= 0.05 else "negative" if compound <= -0.05 else "neutral"

                        existing = (await db.execute(
                            select(SocialPost).where(SocialPost.platform_post_id == str(post.get("id")), SocialPost.platform == "reddit")
                        )).scalar_one_or_none()
                        if existing:
                            continue

                        db.add(SocialPost(
                            platform="reddit",
                            platform_post_id=str(post.get("id", "")),
                            keyword_matched=kw.keyword,
                            content=post.get("title", "")[:2000],
                            url=f"https://reddit.com{post.get('permalink', '')}",
                            likes=post.get("score", 0),
                            comments=post.get("num_comments", 0),
                            sentiment_score=compound,
                            sentiment_label=label,
                            posted_at=datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc) if post.get("created_utc") else None,
                        ))
                        new_posts += 1

                kw.last_scanned = datetime.now(timezone.utc)

        await db.commit()
        logger.info("SOCMINT scan complete", new_posts=new_posts)


async def _fetch_reddit(client, keyword: str) -> list:
    try:
        r = await client.get(
            "https://www.reddit.com/search.json",
            params={"q": keyword, "sort": "new", "limit": 25, "t": "day"},
        )
        if r.status_code == 200:
            data = r.json()
            return [p["data"] for p in data.get("data", {}).get("children", [])]
    except Exception as e:
        logger.warning("Reddit fetch failed", keyword=keyword, error=str(e))
    return []
