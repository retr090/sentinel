import httpx

_HEADERS = {"User-Agent": "SENTINEL-OSINT/1.0"}


async def lookup(email: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://leakcheck.io/api/public",
                params={"check": email},
                headers=_HEADERS,
            )
            if r.status_code == 429:
                return {"error": "rate_limited"}
            if r.status_code == 404:
                return {"found": False, "leak_count": 0, "sources": []}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            data = r.json()
            if not data.get("success"):
                return {"found": False, "leak_count": 0, "sources": []}

            sources = data.get("sources", [])
            fields = data.get("fields", [])
            return {
                "found": len(sources) > 0,
                "leak_count": len(sources),
                "sources": sources[:15],
                "fields": fields,
            }
    except Exception as e:
        return {"error": str(e)}
