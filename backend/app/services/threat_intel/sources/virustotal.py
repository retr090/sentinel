import base64
import httpx
from app.core.config import settings

TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_BASE = "https://www.virustotal.com/api/v3"


def _headers() -> dict | None:
    key = getattr(settings, "VIRUSTOTAL_API_KEY", "")
    if not key:
        return None
    return {"x-apikey": key}


def _extract(data: dict, *extra_fields: str) -> dict:
    attrs = data.get("data", {}).get("attributes", {})
    result = {
        "last_analysis_stats": attrs.get("last_analysis_stats", {}),
        "reputation": attrs.get("reputation"),
        "tags": attrs.get("tags", []),
    }
    for f in extra_fields:
        if f in attrs:
            result[f] = attrs[f]
    return result


async def lookup_ip(ip: str) -> dict:
    h = _headers()
    if h is None:
        return {"error": "no_api_key"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{_BASE}/ip_addresses/{ip}", headers=h)
            if r.status_code == 200:
                return _extract(r.json(), "country", "asn", "as_owner")
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def lookup_domain(domain: str) -> dict:
    h = _headers()
    if h is None:
        return {"error": "no_api_key"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{_BASE}/domains/{domain}", headers=h)
            if r.status_code == 200:
                return _extract(r.json(), "registrar", "creation_date")
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def lookup_hash(hash_value: str) -> dict:
    h = _headers()
    if h is None:
        return {"error": "no_api_key"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{_BASE}/files/{hash_value}", headers=h)
            if r.status_code == 200:
                return _extract(r.json(), "meaningful_name", "type_description", "size", "first_submission_date")
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def lookup_url(url: str) -> dict:
    h = _headers()
    if h is None:
        return {"error": "no_api_key"}
    try:
        url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{_BASE}/urls/{url_id}", headers=h)
            if r.status_code == 200:
                return _extract(r.json(), "last_http_response_code", "url")
        return {}
    except Exception:
        return {"error": "source unavailable"}
