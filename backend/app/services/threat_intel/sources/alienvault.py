import httpx
from app.core.config import settings

TIMEOUT = httpx.Timeout(10.0, connect=5.0)

IOC_TYPE_MAP = {
    "ip": "IPv4",
    "domain": "domain",
    "url": "URL",
    "email": "email",
    "hash_md5": "file",
    "hash_sha1": "file",
    "hash_sha256": "file",
    "cve": "cve",
}


async def lookup(ioc_type: str, value: str) -> dict:
    av_type = IOC_TYPE_MAP.get(ioc_type, "domain")
    try:
        headers = {}
        if settings.ALIENVAULT_OTX_KEY:
            headers["X-OTX-API-KEY"] = settings.ALIENVAULT_OTX_KEY
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f"https://otx.alienvault.com/api/v1/indicators/{av_type}/{value}/general",
                headers=headers,
            )
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}
