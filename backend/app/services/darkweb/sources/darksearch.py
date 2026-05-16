import httpx
from datetime import datetime
from typing import List, Dict


async def search(query: str, page: int = 1) -> List[Dict]:
    """Search DarkSearch.io for dark web results. Free API, no key required."""
    results = []
    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "SENTINEL-OSINT/1.0", "Accept": "application/json"},
        ) as client:
            r = await client.get(
                "https://darksearch.io/api/search",
                params={"query": query, "page": page},
            )
            if r.status_code == 429:
                return [{"error": "rate_limited", "source": "darksearch"}]
            if r.status_code != 200:
                return []

            data = r.json()
            for item in data.get("data", []):
                results.append({
                    "title": str(item.get("title", ""))[:500],
                    "url": str(item.get("link", ""))[:2000],
                    "snippet": str(item.get("description", ""))[:500],
                    "source": "darksearch",
                    "keyword_matched": query,
                    "discovered_at": datetime.utcnow().isoformat(),
                })

    except httpx.TimeoutException:
        return [{"error": "timeout", "source": "darksearch"}]
    except Exception as e:
        return [{"error": str(e), "source": "darksearch"}]

    return results
