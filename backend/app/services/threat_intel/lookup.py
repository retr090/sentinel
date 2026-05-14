import asyncio
import json
from typing import Any, Dict

from app.core.redis import cache_get, cache_set
from app.services.threat_intel.detector import detect_ioc_type
from app.services.threat_intel.scorer import calculate_risk_score
from app.services.threat_intel.sources import (
    greynoise, shodan_idb, ipinfo, alienvault, urlhaus, malwarebazaar, threatfox, virustotal,
)

# Sources applicable to each IOC type (used by run_lookup for metadata)
SOURCE_MAP: Dict[str, list] = {
    "ip":         ["shodan", "greynoise", "ipinfo", "alienvault", "urlhaus", "threatfox", "virustotal"],
    "domain":     ["alienvault", "urlhaus", "threatfox", "virustotal"],
    "hash_md5":   ["malwarebazaar", "threatfox", "alienvault", "virustotal"],
    "hash_sha1":  ["malwarebazaar", "threatfox", "alienvault", "virustotal"],
    "hash_sha256":["malwarebazaar", "threatfox", "alienvault", "virustotal"],
    "url":        ["urlhaus", "threatfox", "virustotal"],
    "email":      ["dns", "hunter"],
    "cve":        ["circl_cve", "nvd"],
    "asn":        ["ripe", "ipinfo"],
}


async def enrich_ip(ip: str) -> Dict[str, Any]:
    cache_key = f"ip_enrichment:{ip}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    results = await asyncio.gather(
        shodan_idb.lookup(ip),
        greynoise.lookup(ip),
        ipinfo.lookup(ip),
        alienvault.lookup("ip", ip),
        urlhaus.lookup_host(ip),
        threatfox.lookup(ip),
        virustotal.lookup_ip(ip),
        return_exceptions=True,
    )
    enrichment = {
        "shodan":     results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "greynoise":  results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "ipinfo":     results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
        "alienvault": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
        "urlhaus":    results[4] if not isinstance(results[4], Exception) else {"error": str(results[4])},
        "threatfox":  results[5] if not isinstance(results[5], Exception) else {"error": str(results[5])},
        "virustotal": results[6] if not isinstance(results[6], Exception) else {"error": str(results[6])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


async def enrich_domain(domain: str) -> Dict[str, Any]:
    cache_key = f"domain_enrichment:{domain}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    results = await asyncio.gather(
        alienvault.lookup("domain", domain),
        urlhaus.lookup_host(domain),
        threatfox.lookup(domain),
        virustotal.lookup_domain(domain),
        return_exceptions=True,
    )
    enrichment = {
        "alienvault": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "urlhaus":    results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "threatfox":  results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
        "virustotal": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


async def enrich_hash(hash_value: str) -> Dict[str, Any]:
    cache_key = f"hash_enrichment:{hash_value}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    ioc_type = detect_ioc_type(hash_value)
    results = await asyncio.gather(
        malwarebazaar.lookup(hash_value),
        alienvault.lookup(ioc_type, hash_value),
        threatfox.lookup(hash_value),
        virustotal.lookup_hash(hash_value),
        return_exceptions=True,
    )
    enrichment = {
        "malwarebazaar": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "alienvault":    results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "threatfox":     results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
        "virustotal":    results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


async def enrich_url(url: str) -> Dict[str, Any]:
    cache_key = f"url_enrichment:{url}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    results = await asyncio.gather(
        urlhaus.lookup_url(url),
        threatfox.lookup(url),
        virustotal.lookup_url(url),
        return_exceptions=True,
    )
    enrichment = {
        "urlhaus":    results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "threatfox":  results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "virustotal": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


async def enrich_email(email: str) -> Dict[str, Any]:
    cache_key = f"email_enrichment:{email}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    results = await asyncio.gather(
        _query_email_dns(email),
        _query_hunter_email(email),
        return_exceptions=True,
    )
    enrichment = {
        "dns":    results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "hunter": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


async def enrich_cve(cve_id: str) -> Dict[str, Any]:
    cve_upper = cve_id.upper()
    cache_key = f"cve_enrichment:{cve_upper}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    results = await asyncio.gather(
        _query_circl_cve(cve_upper),
        _query_nvd_cve(cve_upper),
        return_exceptions=True,
    )
    enrichment = {
        "circl_cve": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "nvd":       results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=86400)
    return enrichment


async def enrich_asn(asn: str) -> Dict[str, Any]:
    asn_num = asn.upper().lstrip("AS")
    cache_key = f"asn_enrichment:{asn_num}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    results = await asyncio.gather(
        _query_ripe_asn(asn_num),
        ipinfo.lookup_asn(asn_num),
        return_exceptions=True,
    )
    enrichment = {
        "ripe":   results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "ipinfo": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=86400)
    return enrichment


async def enrich_ioc(value: str) -> Dict[str, Any]:
    """Universal entry point — detects type and dispatches to the right enricher."""
    ioc_type = detect_ioc_type(value.strip())
    if ioc_type == "ip":
        return await enrich_ip(value.strip())
    elif ioc_type == "domain":
        return await enrich_domain(value.strip())
    elif ioc_type in ("hash_md5", "hash_sha1", "hash_sha256"):
        return await enrich_hash(value.strip())
    elif ioc_type == "url":
        return await enrich_url(value.strip())
    elif ioc_type == "email":
        return await enrich_email(value.strip())
    elif ioc_type == "cve":
        return await enrich_cve(value.strip())
    elif ioc_type == "asn":
        return await enrich_asn(value.strip())
    return await enrich_domain(value.strip())


async def run_lookup(value: str) -> Dict[str, Any]:
    """Full enrichment returning a structured result dict with metadata."""
    v = value.strip()
    ioc_type = detect_ioc_type(v)
    enrichments = await enrich_ioc(v)
    risk_score, risk_level = calculate_risk_score(enrichments)
    return {
        "value": v,
        "ioc_type": ioc_type,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "sources": enrichments,
        "applicable_sources": SOURCE_MAP.get(ioc_type, list(enrichments.keys())),
    }


# ─── inline helpers for email / CVE / ASN ────────────────────────────────────

import httpx as _httpx

_TIMEOUT = _httpx.Timeout(10.0, connect=5.0)
_LONG_TIMEOUT = _httpx.Timeout(15.0, connect=5.0)


async def _query_email_dns(email: str) -> Dict:
    try:
        import dns.resolver
        domain = email.split("@")[-1].lower()
        DISPOSABLE = {
            "guerrillamail.com", "mailinator.com", "tempmail.com", "throwaway.email",
            "sharklasers.com", "spam4.me", "trashmail.com", "yopmail.com",
            "maildrop.cc", "dispostable.com", "fakeinbox.com", "getnada.com",
        }
        result: Dict = {"domain": domain, "disposable": domain in DISPOSABLE}
        try:
            loop = asyncio.get_event_loop()
            mx = await loop.run_in_executor(None, lambda: list(dns.resolver.resolve(domain, "MX")))
            result["mx_records"] = [str(r.exchange).rstrip(".") for r in mx]
            result["has_mx"] = True
        except Exception:
            result["mx_records"] = []
            result["has_mx"] = False
        return result
    except Exception:
        return {"error": "source unavailable"}


async def _query_hunter_email(email: str) -> Dict:
    from app.core.config import settings
    if not settings.HUNTER_IO_KEY:
        return {}
    try:
        async with _httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                "https://api.hunter.io/v2/email-verifier",
                params={"email": email, "api_key": settings.HUNTER_IO_KEY},
            )
            if r.status_code == 200:
                return r.json().get("data", {})
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def _query_circl_cve(cve_id: str) -> Dict:
    try:
        async with _httpx.AsyncClient(timeout=_LONG_TIMEOUT) as client:
            r = await client.get(
                f"https://cve.circl.lu/api/cve/{cve_id}",
                headers={"User-Agent": "SENTINEL-OSINT/1.0"},
            )
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def _query_nvd_cve(cve_id: str) -> Dict:
    try:
        async with _httpx.AsyncClient(timeout=_LONG_TIMEOUT) as client:
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
    except Exception:
        return {"error": "source unavailable"}


async def _query_ripe_asn(asn_num: str) -> Dict:
    try:
        async with _httpx.AsyncClient(timeout=_TIMEOUT) as client:
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
    except Exception:
        return {"error": "source unavailable"}
