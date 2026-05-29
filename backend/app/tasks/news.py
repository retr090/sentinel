from celery import shared_task
from celery.utils.log import get_task_logger
import asyncio
import json
import re
from typing import Optional
from bs4 import BeautifulSoup

logger = get_task_logger(__name__)

DEFAULT_RSS_SOURCES = [
    # ── Sri Lanka — English (15) ──────────────────────────────────────────────
    {"name": "Daily FT", "url": "https://www.ft.lk/rss", "category": "regional", "language": "en"},
    {"name": "Colombo Gazette", "url": "https://colombogazette.com/feed/", "category": "regional", "language": "en"},
    {"name": "Ada Derana", "url": "https://www.adaderana.lk/rss.asp", "category": "regional", "language": "en"},
    {"name": "Daily Mirror LK", "url": "https://www.dailymirror.lk/rss/", "category": "regional", "language": "en"},
    {"name": "The Island LK", "url": "https://island.lk/feed/", "category": "regional", "language": "en"},
    {"name": "Economy Next", "url": "https://economynext.com/feed/", "category": "regional", "language": "en"},
    {"name": "Lanka Business Online", "url": "https://www.lankabusinessonline.com/feed/", "category": "regional", "language": "en"},
    {"name": "Newswire LK", "url": "https://www.newswire.lk/feed/", "category": "regional", "language": "en"},
    {"name": "Ground Views", "url": "https://groundviews.org/feed/", "category": "regional", "language": "en"},
    {"name": "LankaWeb", "url": "https://www.lankaweb.com/news/rss.xml", "category": "regional", "language": "en"},
    {"name": "Sunday Observer LK", "url": "https://www.sundayobserver.lk/rss.xml", "category": "regional", "language": "en"},
    {"name": "Ceylon Today", "url": "https://www.ceylontoday.lk/rss", "category": "regional", "language": "en"},
    {"name": "News First LK", "url": "https://www.newsfirst.lk/feed/", "category": "regional", "language": "en"},
    {"name": "Daily News LK", "url": "https://www.dailynews.lk/rss.xml", "category": "regional", "language": "en"},
    {"name": "The Morning LK", "url": "https://www.themorning.lk/feed/", "category": "regional", "language": "en"},

    # ── Sri Lanka — Sinhala (10) ──────────────────────────────────────────────
    {"name": "BBC Sinhala", "url": "https://feeds.bbci.co.uk/sinhala/rss.xml", "category": "regional", "language": "si"},
    {"name": "Ada Derana Sinhala", "url": "https://si.adaderana.lk/rss.asp", "category": "regional", "language": "si"},
    {"name": "Lankadeepa", "url": "https://www.lankadeepa.lk/rss", "category": "regional", "language": "si"},
    {"name": "Dinamina", "url": "https://www.dinamina.lk/rss.xml", "category": "regional", "language": "si"},
    {"name": "Divaina", "url": "https://www.divaina.com/rss", "category": "regional", "language": "si"},
    {"name": "Silumina", "url": "https://www.silumina.lk/rss", "category": "regional", "language": "si"},
    {"name": "Lankabima", "url": "https://www.lankabima.lk/feed", "category": "regional", "language": "si"},
    {"name": "Hiru News Sinhala", "url": "https://www.hirunews.lk/feed", "category": "regional", "language": "si"},
    {"name": "Mawbima", "url": "https://www.mawbima.lk/rss", "category": "regional", "language": "si"},
    {"name": "Rivira", "url": "https://www.rivira.lk/feed/", "category": "regional", "language": "si"},

    # ── Sri Lanka — Tamil (7) ─────────────────────────────────────────────────
    {"name": "BBC Tamil", "url": "https://feeds.bbci.co.uk/tamil/rss.xml", "category": "regional", "language": "ta"},
    {"name": "Virakesari", "url": "https://www.virakesari.lk/rss", "category": "regional", "language": "ta"},
    {"name": "Thinakaran", "url": "https://www.thinakaran.lk/rss", "category": "regional", "language": "ta"},
    {"name": "Tamil Guardian", "url": "https://www.tamilguardian.com/rss", "category": "regional", "language": "ta"},
    {"name": "Sudar Oli", "url": "https://sudaroli.lk/feed/", "category": "regional", "language": "ta"},
    {"name": "Uthayan", "url": "https://www.uthayan.com/rss", "category": "regional", "language": "ta"},
    {"name": "Eelanadu", "url": "https://www.eelanadu.ca/feed/", "category": "regional", "language": "ta"},

    # ── India / South Asia — English (12) ────────────────────────────────────
    {"name": "The Hindu", "url": "https://www.thehindu.com/feeder/default.rss", "category": "regional", "language": "en"},
    {"name": "Hindustan Times", "url": "https://www.hindustantimes.com/rss/topnews/rssfeed.xml", "category": "regional", "language": "en"},
    {"name": "The Wire India", "url": "https://thewire.in/rss", "category": "regional", "language": "en"},
    {"name": "Scroll.in", "url": "https://scroll.in/rss", "category": "regional", "language": "en"},
    {"name": "The Print India", "url": "https://theprint.in/feed/", "category": "regional", "language": "en"},
    {"name": "ANI News", "url": "https://aninews.in/rss/", "category": "regional", "language": "en"},
    {"name": "WION", "url": "https://www.wionews.com/rss", "category": "regional", "language": "en"},
    {"name": "ORF India", "url": "https://www.orfonline.org/feed/", "category": "military", "language": "en"},
    {"name": "South Asia Monitor", "url": "https://southasiamonitor.org/feed/", "category": "regional", "language": "en"},
    {"name": "Indian Defence Review", "url": "https://www.indiandefencereview.com/feed/", "category": "military", "language": "en"},
    {"name": "Asia Times", "url": "https://asiatimes.com/feed/", "category": "regional", "language": "en"},
    {"name": "Economic Times India", "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms", "category": "regional", "language": "en"},

    # ── Cyber / Security — English (20) ──────────────────────────────────────
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews", "category": "cyber", "language": "en"},
    {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/", "category": "cyber", "language": "en"},
    {"name": "Bleeping Computer", "url": "https://www.bleepingcomputer.com/feed/", "category": "cyber", "language": "en"},
    {"name": "Dark Reading", "url": "https://www.darkreading.com/rss.xml", "category": "cyber", "language": "en"},
    {"name": "SecurityWeek", "url": "https://feeds.feedburner.com/Securityweek", "category": "cyber", "language": "en"},
    {"name": "SANS Internet Storm Center", "url": "https://isc.sans.edu/rssfeed.xml", "category": "cyber", "language": "en"},
    {"name": "Infosecurity Magazine", "url": "https://www.infosecurity-magazine.com/rss/news/", "category": "cyber", "language": "en"},
    {"name": "CyberScoop", "url": "https://cyberscoop.com/feed/", "category": "cyber", "language": "en"},
    {"name": "SC Magazine", "url": "https://www.scmagazine.com/feed/", "category": "cyber", "language": "en"},
    {"name": "Ars Technica Security", "url": "https://feeds.arstechnica.com/arstechnica/security", "category": "cyber", "language": "en"},
    {"name": "Recorded Future Blog", "url": "https://www.recordedfuture.com/feed", "category": "cyber", "language": "en"},
    {"name": "Malwarebytes Blog", "url": "https://www.malwarebytes.com/blog/feed", "category": "cyber", "language": "en"},
    {"name": "Sophos Naked Security", "url": "https://nakedsecurity.sophos.com/feed/", "category": "cyber", "language": "en"},
    {"name": "CISA Advisories", "url": "https://www.cisa.gov/uscert/ncas/alerts.xml", "category": "cyber", "language": "en"},
    {"name": "Palo Alto Unit42", "url": "https://unit42.paloaltonetworks.com/feed/", "category": "cyber", "language": "en"},
    {"name": "Graham Cluley Blog", "url": "https://grahamcluley.com/feed/", "category": "cyber", "language": "en"},
    {"name": "Schneier on Security", "url": "https://www.schneier.com/blog/atom.xml", "category": "cyber", "language": "en"},
    {"name": "WeLiveSecurity (ESET)", "url": "https://www.welivesecurity.com/en/feed/", "category": "cyber", "language": "en"},
    {"name": "Help Net Security", "url": "https://www.helpnetsecurity.com/feed/", "category": "cyber", "language": "en"},
    {"name": "Threatpost", "url": "https://threatpost.com/feed/", "category": "cyber", "language": "en"},

    # ── Military / Geopolitical — English (16) ───────────────────────────────
    {"name": "The Diplomat", "url": "https://thediplomat.com/feed/", "category": "military", "language": "en"},
    {"name": "Defense News", "url": "https://www.defensenews.com/arc/outboundfeeds/rss/", "category": "military", "language": "en"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "category": "military", "language": "en"},
    {"name": "Bellingcat", "url": "https://www.bellingcat.com/feed/", "category": "military", "language": "en"},
    {"name": "War on the Rocks", "url": "https://warontherocks.com/feed/", "category": "military", "language": "en"},
    {"name": "Foreign Policy", "url": "https://foreignpolicy.com/feed/", "category": "military", "language": "en"},
    {"name": "Carnegie Endowment", "url": "https://carnegieendowment.org/rss/solr/?fa=news", "category": "military", "language": "en"},
    {"name": "Deutsche Welle World", "url": "https://rss.dw.com/rdf/rss-en-all", "category": "military", "language": "en"},
    {"name": "France 24 English", "url": "https://www.france24.com/en/rss", "category": "military", "language": "en"},
    {"name": "South China Morning Post", "url": "https://www.scmp.com/rss/5/feed", "category": "military", "language": "en"},
    {"name": "Military Times", "url": "https://www.militarytimes.com/arc/outboundfeeds/rss/", "category": "military", "language": "en"},
    {"name": "Breaking Defense", "url": "https://breakingdefense.com/feed/", "category": "military", "language": "en"},
    {"name": "Indo-Pacific Defense Forum", "url": "https://ipdefenseforum.com/feed/", "category": "military", "language": "en"},
    {"name": "RAND Corporation", "url": "https://www.rand.org/rss.xml", "category": "military", "language": "en"},
    {"name": "FDD Research", "url": "https://www.fdd.org/feed/", "category": "military", "language": "en"},
    {"name": "Stimson Center", "url": "https://www.stimson.org/feed/", "category": "military", "language": "en"},

    # ── General / International — English (11) ───────────────────────────────
    {"name": "Reuters World", "url": "https://feeds.reuters.com/reuters/worldNews", "category": "general", "language": "en"},
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "general", "language": "en"},
    {"name": "BBC South Asia", "url": "https://feeds.bbci.co.uk/news/world/south_asia/rss.xml", "category": "general", "language": "en"},
    {"name": "NHK World Japan", "url": "https://www3.nhk.or.jp/nhkworld/upld/medias/en/rss/latest.xml", "category": "general", "language": "en"},
    {"name": "Times of India", "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "category": "general", "language": "en"},
    {"name": "Global Voices", "url": "https://globalvoices.org/feed/", "category": "general", "language": "en"},
    {"name": "Straits Times Asia", "url": "https://www.straitstimes.com/global/rss", "category": "general", "language": "en"},
    {"name": "Channel News Asia", "url": "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml", "category": "general", "language": "en"},
    {"name": "Indian Express", "url": "https://indianexpress.com/feed/", "category": "general", "language": "en"},
    {"name": "Deutsche Welle Asia", "url": "https://rss.dw.com/rdf/rss-en-asi", "category": "general", "language": "en"},
    {"name": "Reuters India", "url": "https://feeds.reuters.com/reuters/INtopNews", "category": "general", "language": "en"},
]

_NEWS_ANALYSIS_PROMPT = """\
You are a threat intelligence analyst for a Sri Lanka national security platform.
Analyse each news article for operational relevance to Sri Lanka's security interests.
Consider: Sri Lanka (direct coverage), South Asia geopolitics, cyber threats affecting LK organisations,
military/defence developments in the region, economic security, critical infrastructure.

Articles (JSON array):
{articles}

Respond with ONLY a valid JSON array of objects — same order, no markdown, no comments, no trailing commas:
[{{
  "id": <id>,
  "score": 0.0-1.0,
  "label": "high"|"medium"|"low"|"irrelevant",
  "category": "cyber"|"military"|"geopolitical"|"economic"|"civil_unrest"|"crime"|"public_health"|"general",
  "risk_level": "critical"|"high"|"medium"|"low"|"none",
  "event_type": "specific event type in 2-5 words",
  "key_points": ["fact or signal 1", "fact or signal 2", "fact or signal 3"],
  "security_implications": ["why this matters operationally", "possible second-order effect"],
  "entities": ["notable country, organisation, malware, actor, sector, or location names"],
  "locations": ["notable geographic locations"],
  "watch_terms": ["terms analysts should monitor next"],
  "recommended_action": "short analyst action, or 'Monitor only'",
  "confidence": "high"|"medium"|"low"
}}]

Scoring guide:
- high (0.75-1.0): directly about Sri Lanka or immediate threat to LK assets
- medium (0.40-0.74): South Asia / Indian Ocean region, or generic cyber threat affecting LK sector
- low (0.10-0.39): tangentially related geopolitics or global security news
- irrelevant (0.0-0.09): no relevance to Sri Lanka or its security context

Rules: be factual, do not invent facts, base output only on title/snippet/article_text/source/category/language. Use article_text as the primary context when available. Do not write article summaries; extract intelligence signals and operational implications. Every string must be valid JSON with internal quotes escaped or omitted.
"""


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _extract_json(text: str) -> Optional[list]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_article_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()

    candidates = []
    for selector in ("article", "main", "[role=main]", ".article", ".post", ".entry-content", ".story-body"):
        for node in soup.select(selector):
            text = _clean_text(node.get_text(" "))
            if len(text) > 300:
                candidates.append(text)

    if not candidates:
        paragraphs = [_clean_text(p.get_text(" ")) for p in soup.find_all("p")]
        text = " ".join(p for p in paragraphs if len(p) > 40)
    else:
        text = max(candidates, key=len)

    # Keep enough context for analyst review and AI analysis without bloating rows.
    return text[:8000]


async def _fetch_article_text(client, url: str) -> str:
    try:
        r = await client.get(url)
        content_type = r.headers.get("content-type", "")
        if r.status_code != 200 or "html" not in content_type.lower():
            return ""
        return _extract_article_text(r.text)
    except Exception:
        return ""


async def _score_batch(articles: list) -> list:
    """Call Groq to score and analyse a batch of articles. Returns analysed list or empty on failure."""
    from app.core.config import settings
    if not settings.GROQ_API_KEY:
        return []

    payload = [
        {
            "id": a["id"],
            "title": a["title"],
            "snippet": (a.get("snippet") or "")[:700],
            "article_text": (a.get("article_text") or "")[:2200],
            "source": a.get("source"),
            "category": a.get("category"),
            "language": a.get("language"),
        }
        for a in articles
    ]
    prompt = _NEWS_ANALYSIS_PROMPT.format(articles=json.dumps(payload, ensure_ascii=False))

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        resp = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Return strict valid JSON only. Do not include markdown. Escape internal quotes in strings.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=900,
        )
        raw = resp.choices[0].message.content or ""
        result = _extract_json(raw)
        return result or []
    except Exception as exc:
        logger.warning(f"Groq news analysis failed: {exc}")
        return []


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


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    queue="feeds",
    name="app.tasks.news.score_news_relevance",
)
def score_news_relevance(self):
    try:
        run_async(_score_news_relevance_async())
    except Exception as exc:
        logger.error("score_news_relevance failed", exc_info=True)
        raise self.retry(exc=exc, countdown=120)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    queue="feeds",
    name="app.tasks.news.backfill_article_text",
)
def backfill_article_text(self):
    try:
        run_async(_backfill_article_text_async())
    except Exception as exc:
        logger.error("backfill_article_text failed", exc_info=True)
        raise self.retry(exc=exc, countdown=120)


async def _fetch_all_news_async():
    import feedparser
    import httpx
    from app.core.database import AsyncSessionLocal
    from app.models.news import NewsSource, NewsArticle, NewsKeyword, NewsAlert
    from sqlalchemy import select, func
    from datetime import datetime, timezone, timedelta
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

        # Load active keywords once
        kw_result = await db.execute(select(NewsKeyword).where(NewsKeyword.is_active == True))
        keywords = kw_result.scalars().all()

        new_articles = []
        headers = {"User-Agent": "Mozilla/5.0 (compatible; SentinelBot/1.0; +https://sentinel.internal)"}
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0), headers=headers, follow_redirects=True) as client:
            for source in sources:
                try:
                    r = await client.get(source.url)
                    if r.status_code != 200:
                        logger.warning(f"RSS fetch non-200: {source.name} status={r.status_code}")
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
                        full_text = await _fetch_article_text(client, url)

                        sentiment = sia.polarity_scores(title + " " + summary)
                        compound = sentiment["compound"]
                        label = "positive" if compound >= 0.05 else "negative" if compound <= -0.05 else "neutral"

                        published = None
                        if entry.get("published_parsed"):
                            import time
                            published = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)

                        # Keyword matching
                        text_lower = (title + " " + summary).lower()
                        matched_kws = [kw.keyword for kw in keywords if kw.keyword.lower() in text_lower]

                        article = NewsArticle(
                            source_id=source.id,
                            title=title,
                            url=url,
                            content_snippet=summary,
                            full_text=full_text or None,
                            author=entry.get("author"),
                            category=source.category,
                            sentiment_score=compound,
                            sentiment_label=label,
                            language=source.language,
                            keywords_matched=matched_kws,
                            raw_data={"source": source.name, "full_text_extracted": bool(full_text)},
                            published_at=published,
                        )
                        db.add(article)
                        new_articles.append({"title": title, "matched_kws": matched_kws})

                    source.last_fetched = datetime.now(timezone.utc)
                except Exception as e:
                    logger.warning(f"RSS fetch failed: {source.name}: {e}")

        await db.commit()

        # Check keyword alert thresholds
        if keywords:
            window_start = datetime.now(timezone.utc) - timedelta(hours=1)
            for kw in keywords:
                count_result = await db.execute(
                    select(func.count()).select_from(NewsArticle).where(
                        NewsArticle.created_at >= window_start,
                        NewsArticle.keywords_matched.contains([kw.keyword]),
                    )
                )
                mention_count = count_result.scalar() or 0
                if mention_count >= kw.alert_threshold:
                    # Avoid duplicate alerts within the same hour
                    existing_alert = await db.execute(
                        select(NewsAlert).where(
                            NewsAlert.keyword == kw.keyword,
                            NewsAlert.triggered_at >= window_start,
                        )
                    )
                    if not existing_alert.scalar_one_or_none():
                        severity = "CRITICAL" if mention_count >= kw.alert_threshold * 3 else "HIGH" if mention_count >= kw.alert_threshold * 2 else "MEDIUM"
                        db.add(NewsAlert(
                            keyword_id=kw.id,
                            keyword=kw.keyword,
                            mention_count=mention_count,
                            window_hours=1,
                            severity=severity,
                        ))
            await db.commit()

        logger.info(f"News fetch complete: {len(new_articles)} new articles")


async def _score_news_relevance_async():
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.models.news import NewsArticle
    from sqlalchemy import select

    if not settings.GROQ_API_KEY:
        logger.info("score_news_relevance: GROQ_API_KEY not set, skipping")  # noqa: structlog-style ok here
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsArticle)
            .where(NewsArticle.is_archived == False)
            .order_by(NewsArticle.created_at.desc())
            .limit(100)
        )
        articles = [
            article for article in result.scalars().all()
            if (
                article.relevance_score is None
                or not article.full_text
                or not isinstance(article.ai_analysis, dict)
                or "key_points" not in article.ai_analysis
            )
        ][:50]

        if not articles:
            return

        # One article per request is slower but avoids one malformed item invalidating a whole batch.
        BATCH = 1
        scored = 0
        for i in range(0, len(articles), BATCH):
            batch = articles[i:i + BATCH]
            payload = [
                {
                    "id": a.id,
                    "title": a.title,
                    "snippet": a.content_snippet or "",
                    "article_text": a.full_text or "",
                    "source": a.raw_data.get("source") if isinstance(a.raw_data, dict) else None,
                    "category": a.category,
                    "language": a.language,
                }
                for a in batch
            ]
            scores = await _score_batch(payload)

            score_map = {s["id"]: s for s in scores if isinstance(s, dict) and "id" in s}
            for article in batch:
                if article.id in score_map:
                    s = score_map[article.id]
                    article.relevance_score = max(0.0, min(1.0, float(s.get("score", 0.0))))
                    article.relevance_label = s.get("label", "low")
                    article.ai_analysis = {
                        "category": s.get("category", article.category or "general"),
                        "risk_level": s.get("risk_level", "none"),
                        "event_type": s.get("event_type", ""),
                        "key_points": s.get("key_points", []) if isinstance(s.get("key_points", []), list) else [],
                        "security_implications": s.get("security_implications", []) if isinstance(s.get("security_implications", []), list) else [],
                        "entities": s.get("entities", []) if isinstance(s.get("entities", []), list) else [],
                        "locations": s.get("locations", []) if isinstance(s.get("locations", []), list) else [],
                        "watch_terms": s.get("watch_terms", []) if isinstance(s.get("watch_terms", []), list) else [],
                        "recommended_action": s.get("recommended_action", "Monitor only"),
                        "confidence": s.get("confidence", "low"),
                        "generated_by": "groq_ai",
                        "model": settings.GROQ_MODEL,
                    }
                    scored += 1

        await db.commit()
        logger.info(f"News relevance scoring complete: {scored}/{len(articles)} scored")


async def _backfill_article_text_async():
    import httpx
    from app.core.database import AsyncSessionLocal
    from app.models.news import NewsArticle
    from sqlalchemy import select

    headers = {"User-Agent": "Mozilla/5.0 (compatible; SentinelBot/1.0; +https://sentinel.internal)"}
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsArticle)
            .where(NewsArticle.is_archived == False, NewsArticle.full_text == None, NewsArticle.url != None)
            .order_by(NewsArticle.created_at.desc())
            .limit(25)
        )
        articles = result.scalars().all()
        if not articles:
            return

        extracted = 0
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0), headers=headers, follow_redirects=True) as client:
            for article in articles:
                text = await _fetch_article_text(client, article.url)
                if text:
                    article.full_text = text
                    raw = article.raw_data if isinstance(article.raw_data, dict) else {}
                    article.raw_data = {**raw, "full_text_extracted": True}
                    # Force analysis refresh with the richer context.
                    article.ai_analysis = None
                    extracted += 1

        await db.commit()
        logger.info(f"Article text backfill complete: {extracted}/{len(articles)} extracted")
