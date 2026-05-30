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
    from app.models.socmint import SocialKeyword, SocialPost, SocialAlert
    from sqlalchemy import select, func
    from datetime import datetime, timezone, timedelta
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    sia = SentimentIntensityAnalyzer()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SocialKeyword).where(SocialKeyword.is_active == True))
        keywords = result.scalars().all()

        new_posts = 0
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=True) as client:
            for kw in keywords:
                platforms = kw.platforms or ["reddit"]
                for platform_entry in platforms:
                    if platform_entry.startswith("reddit"):
                        subreddit = None
                        if ":" in platform_entry:
                            subreddit = platform_entry.split(":", 1)[1].strip()
                        posts = await _fetch_pullpush(client, kw.keyword, subreddit)
                        for post in posts:
                            text = post.get("title", "") + " " + (post.get("selftext", "") or "")
                            sentiment = sia.polarity_scores(text)
                            compound = sentiment["compound"]
                            label = "positive" if compound >= 0.05 else "negative" if compound <= -0.05 else "neutral"

                            existing = (await db.execute(
                                select(SocialPost).where(
                                    SocialPost.platform_post_id == str(post.get("id", "")),
                                    SocialPost.platform == "reddit"
                                )
                            )).scalar_one_or_none()
                            if existing:
                                continue

                            db.add(SocialPost(
                                platform="reddit",
                                platform_post_id=str(post.get("id", "")),
                                keyword_matched=kw.keyword,
                                content=(post.get("title", "") + "\n\n" + (post.get("selftext", "") or "")).strip()[:4000],
                                url=f"https://reddit.com{post.get('permalink', '')}",
                                likes=post.get("score", 0),
                                comments=post.get("num_comments", 0),
                                sentiment_score=compound,
                                sentiment_label=label,
                            raw_data={
                                "subreddit": post.get("subreddit"),
                                "author": post.get("author"),
                                "over_18": post.get("over_18", False),
                                "is_self": post.get("is_self", False),
                                "source": "pullpush.io",
                            },
                            posted_at=datetime.fromtimestamp(float(post.get("created_utc", 0)), tz=timezone.utc) if post.get("created_utc") else None,
                            ))
                            new_posts += 1

                kw.last_scanned = datetime.now(timezone.utc)

        await db.commit()

        for kw in keywords:
            if not kw.alert_on_spike:
                continue
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            count = (await db.execute(
                select(func.count()).select_from(SocialPost).where(
                    SocialPost.keyword_matched == kw.keyword,
                    SocialPost.created_at >= one_hour_ago,
                    SocialPost.is_archived == False,
                )
            )).scalar()
            if count and count >= kw.spike_threshold:
                alert = SocialAlert(
                    keyword_id=kw.id,
                    keyword=kw.keyword,
                    mention_count=count,
                    window_hours=1,
                    severity="HIGH" if count >= kw.spike_threshold * 2 else "MEDIUM",
                )
                db.add(alert)
                logger.warning(f"SOCMINT spike alert: keyword={kw.keyword} count={count} threshold={kw.spike_threshold}")
        await db.commit()

        logger.info(f"SOCMINT scan complete: {new_posts} new posts")


async def _fetch_pullpush(client, keyword: str, subreddit: str = None, limit: int = 50) -> list:
    try:
        params = {
            "q": keyword,
            "size": limit,
            "sort": "desc",
            "sort_type": "created_utc",
        }
        if subreddit:
            params["subreddit"] = subreddit

        r = await client.get(
            "https://api.pullpush.io/reddit/search/submission/",
            params=params,
            headers={"User-Agent": "SENTINEL-OSINT/1.0"},
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("data", [])
        logger.warning(f"pullpush.io fetch non-200: keyword={keyword} subreddit={subreddit} status={r.status_code}")
    except Exception as e:
        logger.warning(f"pullpush.io fetch failed: keyword={keyword} subreddit={subreddit} error={e}")
    return []
