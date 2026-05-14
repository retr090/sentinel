import httpx

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def lookup(ip: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"https://internetdb.shodan.io/{ip}")
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}
