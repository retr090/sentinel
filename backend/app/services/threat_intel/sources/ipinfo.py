import httpx
from app.core.config import settings

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def lookup(ip: str) -> dict:
    try:
        url = f"https://ipinfo.io/{ip}/json"
        if settings.IPINFO_TOKEN:
            url += f"?token={settings.IPINFO_TOKEN}"
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def lookup_asn(asn_num: str) -> dict:
    if not settings.IPINFO_TOKEN:
        return {}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f"https://ipinfo.io/AS{asn_num}/json",
                params={"token": settings.IPINFO_TOKEN},
            )
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}
