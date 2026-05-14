import httpx

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def lookup(value: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                "https://threatfox-api.abuse.ch/api/v1/",
                json={"query": "search_ioc", "search_term": value},
            )
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}
