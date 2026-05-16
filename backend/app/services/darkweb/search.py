import asyncio
from typing import List, Dict, Optional
from app.services.darkweb.sources import ahmia, darksearch
from app.services.darkweb.sources.paste_monitor import check_recent_pastes


async def manual_search(
    query: str,
    sources: Optional[List[str]] = None,
) -> Dict:
    """Run a manual dark web search across multiple clearnet intelligence sources."""
    if sources is None:
        sources = ["ahmia", "darksearch", "pastebin"]

    coros = {}
    if "ahmia" in sources:
        coros["ahmia"] = ahmia.search(query, limit=10)
    if "darksearch" in sources:
        coros["darksearch"] = darksearch.search(query)
    if "pastebin" in sources:
        coros["pastebin"] = check_recent_pastes([query])

    if not coros:
        return {"query": query, "total_results": 0, "results": [], "by_source": {}, "source_status": {}}

    keys = list(coros.keys())
    values = await asyncio.gather(*coros.values(), return_exceptions=True)

    all_results: List[Dict] = []
    by_source: Dict[str, List] = {}
    source_status: Dict[str, str] = {}

    for key, value in zip(keys, values):
        if isinstance(value, Exception):
            source_status[key] = "error"
            by_source[key] = []
            continue

        good = [r for r in value if not r.get("error")]
        errors = [r for r in value if r.get("error")]
        source_status[key] = "error" if errors and not good else "ok"
        by_source[key] = good
        all_results.extend(good)

    return {
        "query": query,
        "total_results": len(all_results),
        "results": all_results,
        "by_source": by_source,
        "source_status": source_status,
    }
