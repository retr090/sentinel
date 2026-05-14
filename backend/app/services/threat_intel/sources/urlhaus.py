import httpx
from app.core.config import settings

TIMEOUT = httpx.Timeout(10.0, connect=5.0)

_BASE = "https://urlhaus-api.abuse.ch/v1/"


def _auth_headers() -> dict:
    return {"Auth-Key": settings.URLHAUS_API_KEY} if getattr(settings, "URLHAUS_API_KEY", "") else {}


async def lookup_host(host: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{_BASE}host/", headers=_auth_headers(), data={"host": host})
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def lookup_url(url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{_BASE}url/", headers=_auth_headers(), data={"url": url})
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}
