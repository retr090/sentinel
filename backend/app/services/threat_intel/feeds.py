import httpx
from app.core.config import settings

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def fetch_otx_pulses() -> list:
    if not settings.ALIENVAULT_OTX_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                "https://otx.alienvault.com/api/v1/pulses/subscribed?limit=20",
                headers={"X-OTX-API-KEY": settings.ALIENVAULT_OTX_KEY},
            )
            if r.status_code == 200:
                return r.json().get("results", [])
    except Exception:
        pass
    return []


async def fetch_threatfox_iocs() -> list:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                "https://threatfox-api.abuse.ch/api/v1/",
                json={"query": "get_iocs", "days": 1},
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("query_status") == "ok":
                    return data.get("data", [])
    except Exception:
        pass
    return []


async def fetch_urlhaus_recent() -> list:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get("https://urlhaus-api.abuse.ch/v1/urls/recent/limit/100/")
            if r.status_code == 200:
                return r.json().get("urls", [])
    except Exception:
        pass
    return []
