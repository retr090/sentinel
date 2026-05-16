import re
import asyncio
import httpx
import feedparser
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

RSS_SOURCES = [
    {
        "name": "DarkWebInformer",
        "slug": "darkwebinformer",
        "url": "https://darkwebinformer.com/feed/",
        "category": "dark_web_news",
        "default_severity": "HIGH",
        "always_include": True,
    },
    {
        "name": "Ransomware.live Blog",
        "slug": "ransomware_live_blog",
        "url": "https://www.ransomware.live/rss.xml",
        "category": "ransomware",
        "default_severity": "HIGH",
        "always_include": True,
    },
    {
        "name": "BleepingComputer",
        "slug": "bleepingcomputer",
        "url": "https://www.bleepingcomputer.com/feed/",
        "category": "breach_news",
        "default_severity": "MEDIUM",
        "filter_keywords": [
            "breach", "leak", "hack", "ransomware",
            "stolen", "exposed", "database", "credentials",
        ],
    },
    {
        "name": "DataBreaches.net",
        "slug": "databreaches",
        "url": "https://www.databreaches.net/feed/",
        "category": "breach_news",
        "default_severity": "MEDIUM",
    },
    {
        "name": "HackManac",
        "slug": "hackmanac",
        "url": "https://hackmanac.com/feed",
        "category": "breach_news",
        "default_severity": "MEDIUM",
    },
    {
        "name": "Krebs on Security",
        "slug": "krebsonsecurity",
        "url": "https://krebsonsecurity.com/feed/",
        "category": "security_news",
        "default_severity": "MEDIUM",
        "filter_keywords": [
            "breach", "hack", "stolen", "ransomware",
            "leak", "asia", "south asia", "government",
        ],
    },
    {
        "name": "The Record",
        "slug": "therecord",
        "url": "https://therecord.media/feed",
        "category": "security_news",
        "default_severity": "MEDIUM",
    },
]

_SRI_LANKA_TERMS = [
    "sri lanka", "srilanka", "colombo", "ceylon",
    ".lk", "south asia", "indian ocean",
]

_STRIP_HTML = re.compile(r"<[^>]+>")


def _parse_feed_date(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc).replace(tzinfo=None)
            except Exception:
                continue
    return datetime.utcnow()


def _is_relevant(
    title: str,
    summary: str,
    keywords: List[str],
    source_filters: Optional[List[str]] = None,
) -> Tuple[bool, str]:
    content = (title + " " + summary).lower()

    if source_filters:
        if not any(f.lower() in content for f in source_filters):
            return False, ""

    for keyword in keywords:
        if keyword.lower() in content:
            return True, keyword

    return False, ""


def _rss_severity(title: str, summary: str, default: str) -> str:
    content = (title + " " + summary).lower()
    if any(t in content for t in _SRI_LANKA_TERMS):
        return "HIGH"
    gov_terms = ["government", "military", "ministry", "central bank", "parliament"]
    if any(t in content for t in gov_terms):
        return "HIGH"
    return default


async def fetch_feed(source: Dict) -> List[Dict]:
    """Fetch and parse a single RSS feed into a list of flat entry dicts."""
    entries = []
    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "SENTINEL-OSINT/1.0 (RSS Reader)"},
        ) as client:
            r = await client.get(source["url"])
            if r.status_code != 200:
                return []

        feed = feedparser.parse(r.text)
        for entry in feed.entries[:20]:
            title = str(getattr(entry, "title", ""))
            link = str(getattr(entry, "link", ""))
            summary = _STRIP_HTML.sub("", str(getattr(entry, "summary", ""))).strip()
            published = _parse_feed_date(entry)

            entries.append({
                "title": title[:500],
                "url": link[:2000],
                "snippet": summary[:500],
                "source": f"rss_{source['slug']}",
                "source_name": source["name"],
                "category": source["category"],
                "default_severity": source["default_severity"],
                "always_include": source.get("always_include", False),
                "filter_keywords": source.get("filter_keywords"),
                "published_at": published,
            })

    except httpx.TimeoutException:
        pass
    except Exception as e:
        print(f"[rss_feeds] fetch error {source['name']}: {e}")

    return entries


async def scan_all_feeds(keywords: List[str]) -> List[Dict]:
    """
    Fetch all RSS feeds concurrently, filter entries by keyword relevance,
    and return matched entries ready for _save_mention().
    """
    tasks = [fetch_feed(source) for source in RSS_SOURCES]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    matches = []
    for source_cfg, feed_entries in zip(RSS_SOURCES, results):
        if isinstance(feed_entries, Exception) or not feed_entries:
            continue

        for entry in feed_entries:
            title = entry["title"]
            snippet = entry["snippet"]

            is_match, matched_kw = _is_relevant(
                title, snippet, keywords, entry.get("filter_keywords")
            )

            if not is_match and entry.get("always_include"):
                is_match = True
                matched_kw = "auto_monitor"

            if not is_match:
                continue

            severity = _rss_severity(title, snippet, entry["default_severity"])

            matches.append({
                "keyword_matched": matched_kw,
                "source": entry["source"],
                "source_url": entry["url"],
                "title": title,
                "snippet": snippet,
                "severity": severity,
                "category": entry["category"],
                "published_at": entry.get("published_at"),
                "raw_data": {"title": title, "link": entry["url"], "feed": entry["source_name"]},
            })

    return matches
