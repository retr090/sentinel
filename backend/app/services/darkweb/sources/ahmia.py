import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict

BASE_URL = "https://ahmia.fi"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html",
    "Accept-Language": "en-US,en;q=0.9",
}


async def search(query: str, limit: int = 10) -> List[Dict]:
    """Search Ahmia.fi for dark web .onion results. No API key required."""
    results = []
    try:
        async with httpx.AsyncClient(
            timeout=30, follow_redirects=True, headers=_HEADERS
        ) as client:
            r = await client.get(f"{BASE_URL}/search/", params={"q": query})
            if r.status_code != 200:
                return []

            soup = BeautifulSoup(r.text, "html.parser")

            items = (
                soup.find_all("li", {"class": "result"})
                or soup.find_all("div", {"class": "result"})
                or soup.select(".results li")
                or soup.select("article")
            )

            for item in items[:limit]:
                try:
                    title_el = (
                        item.find("h4")
                        or item.find("h3")
                        or item.find("a", {"class": "title"})
                    )
                    title = title_el.get_text(strip=True) if title_el else ""

                    link_el = item.find("a")
                    url = ""
                    if link_el:
                        href = link_el.get("href", "")
                        url = href.split("redirect_url=")[-1] if "redirect_url=" in href else href

                    snippet_el = (
                        item.find("p")
                        or item.find("div", {"class": "summary"})
                        or item.find("span", {"class": "description"})
                    )
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                    if title or snippet:
                        results.append({
                            "title": title[:500],
                            "url": url[:2000],
                            "snippet": snippet[:500],
                            "source": "ahmia",
                            "discovered_at": datetime.utcnow().isoformat(),
                        })
                except Exception:
                    continue

    except httpx.TimeoutException:
        return [{"error": "timeout", "source": "ahmia"}]
    except Exception as e:
        return [{"error": str(e), "source": "ahmia"}]

    return results


async def search_multiple_keywords(
    keywords: List[str], limit_per_keyword: int = 5
) -> List[Dict]:
    """Search multiple keywords, deduplicate by URL."""
    all_results = []
    seen_urls: set = set()

    for keyword in keywords:
        results = await search(keyword, limit=limit_per_keyword)
        for r in results:
            if not r.get("error"):
                url = r.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    r["keyword_matched"] = keyword
                    all_results.append(r)

    return all_results
