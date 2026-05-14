import httpx
from app.core.config import settings

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def lookup(ip: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            if settings.GREYNOISE_API_KEY:
                r = await client.get(
                    f"https://api.greynoise.io/v2/noise/context/{ip}",
                    headers={"key": settings.GREYNOISE_API_KEY},
                )
            else:
                r = await client.get(f"https://api.greynoise.io/v3/community/{ip}")
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}
