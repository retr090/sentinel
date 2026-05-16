import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict


async def search_pastebin(keyword: str) -> List[Dict]:
    """Search Pastebin public pastes for a keyword."""
    results = []
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        ) as client:
            r = await client.get("https://pastebin.com/search", params={"q": keyword})
            if r.status_code != 200:
                return []

            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.find_all("div", {"class": "search-result"}) or soup.select(".content ul li")

            for item in items[:5]:
                try:
                    link = item.find("a")
                    if not link:
                        continue
                    href = link.get("href", "")
                    title = link.get_text(strip=True)
                    snippet_el = item.find("p")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                    kw_lower = keyword.lower()
                    if href and (kw_lower in title.lower() or kw_lower in snippet.lower()):
                        results.append({
                            "title": title[:300],
                            "url": (
                                f"https://pastebin.com{href}"
                                if not href.startswith("http")
                                else href
                            ),
                            "snippet": snippet[:300],
                            "source": "pastebin",
                            "keyword_matched": keyword,
                            "discovered_at": datetime.utcnow().isoformat(),
                        })
                except Exception:
                    continue

    except Exception as e:
        return [{"error": str(e), "source": "pastebin"}]

    return results


async def search_rentry(keyword: str) -> List[Dict]:
    """Check Rentry.co search for keyword matches."""
    results = []
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SENTINEL/1.0)"},
        ) as client:
            r = await client.get("https://rentry.co/", params={"search": keyword})
            if r.status_code != 200:
                return []

            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select("a[href^='/']")
            seen: set = set()

            for item in items[:5]:
                try:
                    href = item.get("href", "")
                    title = item.get_text(strip=True)
                    if href and href not in seen and len(href) > 1 and "/" not in href[1:]:
                        seen.add(href)
                        results.append({
                            "title": title or f"Rentry paste: {href}",
                            "url": f"https://rentry.co{href}",
                            "snippet": f"Paste site match for: {keyword}",
                            "source": "rentry",
                            "keyword_matched": keyword,
                            "discovered_at": datetime.utcnow().isoformat(),
                        })
                except Exception:
                    continue

    except Exception:
        pass

    return results


async def check_recent_pastes(keywords: List[str]) -> List[Dict]:
    """Check multiple paste sites for keyword matches."""
    all_results = []

    for keyword in keywords:
        for result in await search_pastebin(keyword):
            if not result.get("error"):
                all_results.append(result)

        for result in await search_rentry(keyword):
            if not result.get("error"):
                all_results.append(result)

    return all_results
