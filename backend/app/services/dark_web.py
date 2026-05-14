import httpx
from typing import Dict, Any, List
from app.core.config import settings
import structlog

logger = structlog.get_logger()
TIMEOUT = httpx.Timeout(15.0, connect=5.0)


async def lookup_hibp(query: str, query_type: str = "email") -> List[Dict]:
    headers = {
        "User-Agent": "SENTINEL-OSINT-Platform/1.0",
        "hibp-api-key": settings.HAVEIBEENPWNED_KEY or "",
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            if query_type == "email":
                r = await client.get(
                    f"https://haveibeenpwned.com/api/v3/breachedaccount/{query}",
                    headers=headers,
                    params={"truncateResponse": "false"},
                )
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 404:
                    return []
            elif query_type == "domain":
                r = await client.get(
                    f"https://haveibeenpwned.com/api/v3/breaches",
                    headers=headers,
                )
                if r.status_code == 200:
                    all_breaches = r.json()
                    return [b for b in all_breaches if query.lower() in b.get("Domain", "").lower()]
    except Exception as e:
        logger.error("HIBP lookup failed", error=str(e))
    return []


async def search_ahmia(keyword: str) -> List[Dict]:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                "https://ahmia.fi/search/",
                params={"q": keyword},
                headers={"User-Agent": "SENTINEL-OSINT/1.0"},
            )
            if r.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, "lxml")
                results = []
                for item in soup.select(".result")[:10]:
                    title_el = item.select_one("h4 a")
                    desc_el = item.select_one(".description")
                    if title_el:
                        results.append({
                            "title": title_el.get_text(strip=True),
                            "url": title_el.get("href", ""),
                            "snippet": desc_el.get_text(strip=True) if desc_el else "",
                            "source": "ahmia",
                        })
                return results
    except Exception as e:
        logger.error("Ahmia search failed", keyword=keyword, error=str(e))
    return []


async def lookup_paste_sites(keyword: str) -> List[Dict]:
    results = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Google Custom Search fallback for paste sites (if configured)
            # For now return empty — paste monitoring is handled by Celery tasks
            pass
    except Exception as e:
        logger.error("Paste lookup failed", error=str(e))
    return results


async def scan_keyword_dark_web(keyword: str) -> List[Dict]:
    findings = []
    ahmia_results = await search_ahmia(keyword)
    for r in ahmia_results:
        findings.append({
            "source": "ahmia",
            "source_url": r.get("url"),
            "title": r.get("title"),
            "snippet": r.get("snippet"),
        })
    return findings
