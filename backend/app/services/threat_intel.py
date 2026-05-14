import asyncio
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.redis import cache_get, cache_set
import json
import structlog

logger = structlog.get_logger()

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def enrich_ip(ip: str) -> Dict[str, Any]:
    """Aggregate IP intelligence from all free sources."""
    cache_key = f"ip_enrichment:{ip}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    tasks = [
        _query_shodan_internetdb(ip),
        _query_greynoise(ip),
        _query_ipinfo(ip),
        _query_alienvault_ip(ip),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    enrichment = {
        "shodan": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "greynoise": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "ipinfo": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
        "alienvault": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


async def enrich_domain(domain: str) -> Dict[str, Any]:
    cache_key = f"domain_enrichment:{domain}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    tasks = [
        _query_alienvault_domain(domain),
        _query_urlhaus_domain(domain),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    enrichment = {
        "alienvault": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "urlhaus": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


async def enrich_hash(hash_value: str) -> Dict[str, Any]:
    cache_key = f"hash_enrichment:{hash_value}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    tasks = [
        _query_malwarebazaar(hash_value),
        _query_alienvault_hash(hash_value),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    enrichment = {
        "malwarebazaar": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "alienvault": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


def calculate_risk_score(enrichments: Dict[str, Any]) -> float:
    score = 0.0
    weights = 0.0

    shodan = enrichments.get("shodan", {})
    if isinstance(shodan, dict) and "vulns" in shodan:
        score += min(len(shodan["vulns"]) * 10, 40)
        weights += 40

    gn = enrichments.get("greynoise", {})
    if isinstance(gn, dict):
        if gn.get("classification") == "malicious":
            score += 50
        elif gn.get("noise"):
            score += 20
        weights += 50

    av = enrichments.get("alienvault", {})
    if isinstance(av, dict) and av.get("pulse_info"):
        pulse_count = av["pulse_info"].get("count", 0)
        score += min(pulse_count * 5, 30)
        weights += 30

    mb = enrichments.get("malwarebazaar", {})
    if isinstance(mb, dict) and mb.get("query_status") == "ok":
        score += 80

    if weights == 0:
        return 0.0
    return min(round((score / max(weights, 100)) * 100, 1), 100.0)


async def _query_shodan_internetdb(ip: str) -> Dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"https://internetdb.shodan.io/{ip}")
        if r.status_code == 200:
            return r.json()
        return {}


async def _query_greynoise(ip: str) -> Dict:
    if not settings.GREYNOISE_API_KEY:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"https://api.greynoise.io/v3/community/{ip}")
            if r.status_code == 200:
                return r.json()
        return {}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            f"https://api.greynoise.io/v2/noise/context/{ip}",
            headers={"key": settings.GREYNOISE_API_KEY},
        )
        if r.status_code == 200:
            return r.json()
    return {}


async def _query_ipinfo(ip: str) -> Dict:
    url = f"https://ipinfo.io/{ip}/json"
    if settings.IPINFO_TOKEN:
        url += f"?token={settings.IPINFO_TOKEN}"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(url)
        if r.status_code == 200:
            return r.json()
    return {}


async def _query_alienvault_ip(ip: str) -> Dict:
    if not settings.ALIENVAULT_OTX_KEY:
        return {}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            f"https://otx.alienvault.com/api/v1/indicators/IPv4/{ip}/general",
            headers={"X-OTX-API-KEY": settings.ALIENVAULT_OTX_KEY},
        )
        if r.status_code == 200:
            return r.json()
    return {}


async def _query_alienvault_domain(domain: str) -> Dict:
    if not settings.ALIENVAULT_OTX_KEY:
        return {}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/general",
            headers={"X-OTX-API-KEY": settings.ALIENVAULT_OTX_KEY},
        )
        if r.status_code == 200:
            return r.json()
    return {}


async def _query_alienvault_hash(hash_value: str) -> Dict:
    if not settings.ALIENVAULT_OTX_KEY:
        return {}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            f"https://otx.alienvault.com/api/v1/indicators/file/{hash_value}/general",
            headers={"X-OTX-API-KEY": settings.ALIENVAULT_OTX_KEY},
        )
        if r.status_code == 200:
            return r.json()
    return {}


async def _query_urlhaus_domain(domain: str) -> Dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            "https://urlhaus-api.abuse.ch/v1/host/",
            data={"host": domain},
        )
        if r.status_code == 200:
            return r.json()
    return {}


async def _query_malwarebazaar(hash_value: str) -> Dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            "https://mb-api.abuse.ch/api/v1/",
            data={"query": "get_info", "hash": hash_value},
        )
        if r.status_code == 200:
            return r.json()
    return {}


async def fetch_otx_pulses() -> list:
    if not settings.ALIENVAULT_OTX_KEY:
        return []
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            "https://otx.alienvault.com/api/v1/pulses/subscribed?limit=20",
            headers={"X-OTX-API-KEY": settings.ALIENVAULT_OTX_KEY},
        )
        if r.status_code == 200:
            return r.json().get("results", [])
    return []


async def fetch_threatfox_iocs() -> list:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            "https://threatfox-api.abuse.ch/api/v1/",
            json={"query": "get_iocs", "days": 1},
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("query_status") == "ok":
                return data.get("data", [])
    return []


async def fetch_urlhaus_recent() -> list:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get("https://urlhaus-api.abuse.ch/v1/urls/recent/limit/100/")
        if r.status_code == 200:
            return r.json().get("urls", [])
    return []
