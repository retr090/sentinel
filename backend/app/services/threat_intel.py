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
        _query_urlhaus_host(ip),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    enrichment = {
        "shodan": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "greynoise": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "ipinfo": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
        "alienvault": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
        "urlhaus": results[4] if not isinstance(results[4], Exception) else {"error": str(results[4])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


async def enrich_email(email: str) -> Dict[str, Any]:
    cache_key = f"email_enrichment:{email}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    tasks = [_query_email_dns(email), _query_hunter_email(email)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    enrichment = {
        "dns": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "hunter": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


async def enrich_cve(cve_id: str) -> Dict[str, Any]:
    cache_key = f"cve_enrichment:{cve_id.upper()}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    enrichment = {"nvd": await _query_nvd_cve(cve_id.upper())}
    await cache_set(cache_key, json.dumps(enrichment), ttl=86400)
    return enrichment


async def enrich_asn(asn: str) -> Dict[str, Any]:
    asn_num = asn.upper().lstrip("AS")
    cache_key = f"asn_enrichment:{asn_num}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    tasks = [_query_ripe_asn(asn_num), _query_ipinfo_asn(asn_num)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    enrichment = {
        "ripe": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "ipinfo": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=86400)
    return enrichment


async def enrich_url(url: str) -> Dict[str, Any]:
    cache_key = f"url_enrichment:{url}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    enrichment = {"urlhaus": await _query_urlhaus_url(url)}
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


async def enrich_domain(domain: str) -> Dict[str, Any]:
    cache_key = f"domain_enrichment:{domain}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    tasks = [
        _query_alienvault_domain(domain),
        _query_urlhaus_host(domain),
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

    # GreyNoise: classification is the strongest signal (max 40)
    gn = enrichments.get("greynoise", {})
    if isinstance(gn, dict) and not gn.get("error"):
        if gn.get("classification") == "malicious":
            score += 40
        elif gn.get("noise"):
            score += 15

    # URLhaus: active malware delivery is high severity (max 35)
    uh = enrichments.get("urlhaus", {})
    if isinstance(uh, dict) and uh.get("query_status") == "ok":
        # URL lookup — single result with url_status directly
        if "url_status" in uh:
            score += 15 if uh.get("url_status") == "online" else 5
        else:
            # Host lookup — urls array
            urls = uh.get("urls") or []
            online = sum(1 for u in urls if u.get("url_status") == "online")
            offline = len(urls) - online
            score += min(online * 15 + offline * 5, 35)

    # MalwareBazaar: confirmed malware sample (max 30)
    mb = enrichments.get("malwarebazaar", {})
    if isinstance(mb, dict) and mb.get("query_status") == "ok":
        score += 30

    # AlienVault OTX pulses: community threat reports (max 20)
    av = enrichments.get("alienvault", {})
    if isinstance(av, dict) and av.get("pulse_info"):
        pulse_count = av["pulse_info"].get("count", 0)
        score += min(pulse_count * 4, 20)

    # Shodan: open vulnerabilities (max 15)
    shodan = enrichments.get("shodan", {})
    if isinstance(shodan, dict) and "vulns" in shodan:
        score += min(len(shodan["vulns"]) * 5, 15)

    # Email DNS: disposable domain or no MX is suspicious
    dns_data = enrichments.get("dns", {})
    if isinstance(dns_data, dict) and not dns_data.get("error"):
        if dns_data.get("disposable"):
            score += 30
        elif not dns_data.get("has_mx"):
            score += 15
    # Hunter.io: undeliverable or risky verdict
    hunter = enrichments.get("hunter", {})
    if isinstance(hunter, dict) and not hunter.get("error"):
        status = (hunter.get("status") or "").lower()
        if status in ("invalid", "disposable"):
            score += 20
        elif status == "risky":
            score += 10

    # CVE: CVSS base score scaled to 100 (max 100)
    nvd = enrichments.get("nvd", {})
    if isinstance(nvd, dict) and not nvd.get("error"):
        try:
            metrics = nvd.get("metrics", {})
            cvss = (
                metrics.get("cvssMetricV31", [{}])[0].get("cvssData", {}).get("baseScore")
                or metrics.get("cvssMetricV30", [{}])[0].get("cvssData", {}).get("baseScore")
                or metrics.get("cvssMetricV2", [{}])[0].get("cvssData", {}).get("baseScore")
            )
            if cvss is not None:
                score += float(cvss) * 10
        except (IndexError, KeyError, TypeError):
            pass

    return min(round(score, 1), 100.0)


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


async def _query_urlhaus_host(host: str) -> Dict:
    if not settings.URLHAUS_API_KEY:
        return {}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            "https://urlhaus-api.abuse.ch/v1/host/",
            headers={"Auth-Key": settings.URLHAUS_API_KEY},
            data={"host": host},
        )
        if r.status_code == 200:
            return r.json()
    return {}


async def _query_urlhaus_url(url: str) -> Dict:
    if not settings.URLHAUS_API_KEY:
        return {}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            "https://urlhaus-api.abuse.ch/v1/url/",
            headers={"Auth-Key": settings.URLHAUS_API_KEY},
            data={"url": url},
        )
        if r.status_code == 200:
            return r.json()
    return {}


async def _query_malwarebazaar(hash_value: str) -> Dict:
    if not settings.URLHAUS_API_KEY:
        return {}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            "https://mb-api.abuse.ch/api/v1/",
            headers={"Auth-Key": settings.URLHAUS_API_KEY},
            data={"query": "get_info", "hash": hash_value},
        )
        if r.status_code == 200:
            return r.json()
    return {}


async def _query_email_dns(email: str) -> Dict:
    import dns.resolver
    domain = email.split("@")[-1].lower()
    DISPOSABLE_DOMAINS = {
        "guerrillamail.com", "mailinator.com", "tempmail.com", "throwaway.email",
        "sharklasers.com", "guerrillamailblock.com", "grr.la", "guerrillamail.info",
        "spam4.me", "trashmail.com", "yopmail.com", "maildrop.cc", "dispostable.com",
        "fakeinbox.com", "getnada.com", "trbvm.com", "filzmail.com", "discard.email",
    }
    result: Dict = {"domain": domain, "disposable": domain in DISPOSABLE_DOMAINS}
    try:
        loop = asyncio.get_event_loop()
        mx_records = await loop.run_in_executor(
            None, lambda: list(dns.resolver.resolve(domain, "MX"))
        )
        result["mx_records"] = [str(r.exchange).rstrip(".") for r in mx_records]
        result["has_mx"] = True
    except Exception:
        result["mx_records"] = []
        result["has_mx"] = False
    return result


async def _query_hunter_email(email: str) -> Dict:
    if not settings.HUNTER_IO_KEY:
        return {}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            "https://api.hunter.io/v2/email-verifier",
            params={"email": email, "api_key": settings.HUNTER_IO_KEY},
        )
        if r.status_code == 200:
            return r.json().get("data", {})
    return {}


async def _query_nvd_cve(cve_id: str) -> Dict:
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        r = await client.get(
            "https://services.nvd.nist.gov/rest/json/cves/2.0",
            params={"cveId": cve_id},
            headers={"User-Agent": "SENTINEL-OSINT/1.0"},
        )
        if r.status_code == 200:
            vulns = r.json().get("vulnerabilities", [])
            if vulns:
                return vulns[0].get("cve", {})
    return {}


async def _query_ripe_asn(asn_num: str) -> Dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        overview, abuse = await asyncio.gather(
            client.get(
                f"https://stat.ripe.net/data/as-overview/data.json?resource=AS{asn_num}",
                headers={"User-Agent": "SENTINEL-OSINT/1.0"},
            ),
            client.get(
                f"https://stat.ripe.net/data/abuse-contact-finder/data.json?resource=AS{asn_num}",
                headers={"User-Agent": "SENTINEL-OSINT/1.0"},
            ),
            return_exceptions=True,
        )
    result = {}
    if not isinstance(overview, Exception) and overview.status_code == 200:
        result.update(overview.json().get("data", {}))
    if not isinstance(abuse, Exception) and abuse.status_code == 200:
        result["abuse_contacts"] = abuse.json().get("data", {}).get("abuse_contacts", [])
    return result


async def _query_ipinfo_asn(asn_num: str) -> Dict:
    if not settings.IPINFO_TOKEN:
        return {}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            f"https://ipinfo.io/AS{asn_num}/json",
            params={"token": settings.IPINFO_TOKEN},
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
