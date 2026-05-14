import asyncio
import re
import httpx
from typing import Dict, Any, Optional, Tuple
from app.core.config import settings
from app.core.redis import cache_get, cache_set
import json
import structlog

logger = structlog.get_logger()

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


# ─────────────────────────────────────────────
# IOC TYPE DETECTION
# ─────────────────────────────────────────────

def detect_ioc_type(value: str) -> str:
    v = value.strip()
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', v):
        return "ip"
    if re.match(r'^[a-fA-F0-9]{32}$', v):
        return "hash_md5"
    if re.match(r'^[a-fA-F0-9]{40}$', v):
        return "hash_sha1"
    if re.match(r'^[a-fA-F0-9]{64}$', v):
        return "hash_sha256"
    if re.match(r'^https?://|^ftp://', v):
        return "url"
    if re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
        return "email"
    if re.match(r'^CVE-\d{4}-\d+$', v, re.IGNORECASE):
        return "cve"
    if re.match(r'^AS\d+$', v, re.IGNORECASE):
        return "asn"
    return "domain"


# ─────────────────────────────────────────────
# RISK SCORING
# ─────────────────────────────────────────────

def calculate_risk_score(enrichments: Dict[str, Any]) -> Tuple[float, str]:
    score = 0.0

    gn = enrichments.get("greynoise", {})
    if isinstance(gn, dict) and not gn.get("error"):
        cls = (gn.get("classification") or "").lower()
        if cls == "malicious":
            score += 30
        elif cls == "benign":
            score -= 20
        if gn.get("noise"):
            score += 10

    av = enrichments.get("alienvault", {})
    if isinstance(av, dict) and not av.get("error"):
        pulse_count = (av.get("pulse_info") or {}).get("count", 0) or 0
        score += min(pulse_count * 3, 20)
        rep = av.get("reputation")
        if rep is not None and rep < 0:
            score += 10

    uh = enrichments.get("urlhaus", {})
    if isinstance(uh, dict) and not uh.get("error"):
        if uh.get("query_status") == "ok":
            urls = uh.get("urls") or []
            online = sum(1 for u in urls if isinstance(u, dict) and u.get("url_status") == "online")
            offline = len(urls) - online
            score += min(online * 15 + offline * 5, 35)
            if uh.get("url_status") == "online":
                score += 25

    tf = enrichments.get("threatfox", {})
    if isinstance(tf, dict) and not tf.get("error"):
        if tf.get("query_status") == "ok":
            data = tf.get("data") or []
            if data and isinstance(data, list):
                conf = data[0].get("confidence_level", 0) or 0
                score += min(conf / 5.0, 15)

    mb = enrichments.get("malwarebazaar", {})
    if isinstance(mb, dict) and not mb.get("error"):
        if mb.get("query_status") == "ok":
            score += 25

    vt = enrichments.get("virustotal", {})
    if isinstance(vt, dict) and not vt.get("error"):
        stats = vt.get("last_analysis_stats") or {}
        mal = stats.get("malicious", 0) or 0
        if mal > 5:
            score += 20
        elif mal > 0:
            score += 10

    shodan = enrichments.get("shodan", {})
    if isinstance(shodan, dict) and not shodan.get("error"):
        vulns = shodan.get("vulns") or []
        score += min(len(vulns) * 5, 15)

    dns_data = enrichments.get("dns", {})
    if isinstance(dns_data, dict) and not dns_data.get("error"):
        if dns_data.get("disposable"):
            score += 30
        elif not dns_data.get("has_mx"):
            score += 15

    hunter = enrichments.get("hunter", {})
    if isinstance(hunter, dict) and not hunter.get("error"):
        status = (hunter.get("status") or "").lower()
        if status in ("invalid", "disposable"):
            score += 20
        elif status == "risky":
            score += 10

    nvd = enrichments.get("nvd", {})
    circl = enrichments.get("circl_cve", {})
    for cve_data in [nvd, circl]:
        if isinstance(cve_data, dict) and not cve_data.get("error"):
            try:
                cvss = (
                    cve_data.get("cvss")
                    or (cve_data.get("metrics", {}).get("cvssMetricV31", [{}])[0].get("cvssData", {}).get("baseScore"))
                    or (cve_data.get("metrics", {}).get("cvssMetricV30", [{}])[0].get("cvssData", {}).get("baseScore"))
                    or (cve_data.get("metrics", {}).get("cvssMetricV2", [{}])[0].get("cvssData", {}).get("baseScore"))
                )
                if cvss is not None:
                    score += float(cvss) * 10
                    break
            except (IndexError, KeyError, TypeError, ValueError):
                pass

    score = max(0.0, min(100.0, round(score, 1)))

    if score >= 75:
        level = "critical"
    elif score >= 50:
        level = "high"
    elif score >= 25:
        level = "medium"
    elif score > 0:
        level = "low"
    else:
        level = "clean"

    return score, level


# ─────────────────────────────────────────────
# RETRY WRAPPER
# ─────────────────────────────────────────────

async def _with_retry(coro_fn, *args, attempts=3, base_delay=1.0):
    last_exc = None
    for attempt in range(attempts):
        try:
            return await coro_fn(*args)
        except Exception as exc:
            last_exc = exc
            if attempt < attempts - 1:
                await asyncio.sleep(base_delay * (2 ** attempt))
    return {"error": "source unavailable"}


# ─────────────────────────────────────────────
# ORCHESTRATORS
# ─────────────────────────────────────────────

async def enrich_ip(ip: str) -> Dict[str, Any]:
    cache_key = f"ip_enrichment:{ip}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    tasks = [
        _query_shodan_internetdb(ip),
        _query_greynoise(ip),
        _query_ipinfo(ip),
        _query_alienvault("IPv4", ip),
        _query_urlhaus_host(ip),
        _query_threatfox_ioc(ip),
        _query_virustotal_ip(ip),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    enrichment = {
        "shodan": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "greynoise": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "ipinfo": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
        "alienvault": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
        "urlhaus": results[4] if not isinstance(results[4], Exception) else {"error": str(results[4])},
        "threatfox": results[5] if not isinstance(results[5], Exception) else {"error": str(results[5])},
        "virustotal": results[6] if not isinstance(results[6], Exception) else {"error": str(results[6])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


async def enrich_domain(domain: str) -> Dict[str, Any]:
    cache_key = f"domain_enrichment:{domain}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    tasks = [
        _query_alienvault("domain", domain),
        _query_urlhaus_host(domain),
        _query_threatfox_ioc(domain),
        _query_virustotal_domain(domain),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    enrichment = {
        "alienvault": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "urlhaus": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "threatfox": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
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
    hash_len = len(hash_value)
    av_type = "file"

    tasks = [
        _query_malwarebazaar(hash_value),
        _query_alienvault(av_type, hash_value),
        _query_threatfox_ioc(hash_value),
        _query_virustotal_hash(hash_value),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    enrichment = {
        "malwarebazaar": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "alienvault": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "threatfox": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
        "virustotal": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
    }
    await cache_set(cache_key, json.dumps(enrichment), ttl=3600)
    return enrichment


async def enrich_url(url: str) -> Dict[str, Any]:
    cache_key = f"url_enrichment:{url}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    tasks = [
        _query_urlhaus_url(url),
        _query_threatfox_ioc(url),
        _query_virustotal_url(url),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    enrichment = {
        "urlhaus": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "threatfox": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "virustotal": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
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
    cve_upper = cve_id.upper()
    cache_key = f"cve_enrichment:{cve_upper}"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)

    tasks = [_query_circl_cve(cve_upper), _query_nvd_cve(cve_upper)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    enrichment = {
        "circl_cve": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "nvd": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
    }
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


async def enrich_ioc(value: str) -> Dict[str, Any]:
    """Universal entry point — detects type and calls the right enricher."""
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
    else:
        return await enrich_domain(value.strip())


# ─────────────────────────────────────────────
# SOURCE IMPLEMENTATIONS
# ─────────────────────────────────────────────

async def _query_shodan_internetdb(ip: str) -> Dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"https://internetdb.shodan.io/{ip}")
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def _query_greynoise(ip: str) -> Dict:
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


async def _query_ipinfo(ip: str) -> Dict:
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


async def _query_alienvault(av_type: str, value: str) -> Dict:
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


async def _query_urlhaus_host(host: str) -> Dict:
    try:
        headers = {}
        if settings.URLHAUS_API_KEY:
            headers["Auth-Key"] = settings.URLHAUS_API_KEY
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                "https://urlhaus-api.abuse.ch/v1/host/",
                headers=headers,
                data={"host": host},
            )
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def _query_urlhaus_url(url: str) -> Dict:
    try:
        headers = {}
        if settings.URLHAUS_API_KEY:
            headers["Auth-Key"] = settings.URLHAUS_API_KEY
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                "https://urlhaus-api.abuse.ch/v1/url/",
                headers=headers,
                data={"url": url},
            )
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def _query_malwarebazaar(hash_value: str) -> Dict:
    try:
        headers = {}
        if settings.URLHAUS_API_KEY:
            headers["Auth-Key"] = settings.URLHAUS_API_KEY
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                "https://mb-api.abuse.ch/api/v1/",
                headers=headers,
                data={"query": "get_info", "hash": hash_value},
            )
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def _query_threatfox_ioc(value: str) -> Dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                "https://threatfox-api.abuse.ch/api/v1/",
                json={"query": "search_ioc", "search_term": value},
            )
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def _query_virustotal_ip(ip: str) -> Dict:
    if not settings.VIRUSTOTAL_API_KEY:
        return {}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
                headers={"x-apikey": settings.VIRUSTOTAL_API_KEY},
            )
            if r.status_code == 200:
                data = r.json()
                attrs = data.get("data", {}).get("attributes", {})
                return {
                    "last_analysis_stats": attrs.get("last_analysis_stats", {}),
                    "reputation": attrs.get("reputation"),
                    "tags": attrs.get("tags", []),
                    "country": attrs.get("country"),
                    "asn": attrs.get("asn"),
                    "as_owner": attrs.get("as_owner"),
                }
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def _query_virustotal_domain(domain: str) -> Dict:
    if not settings.VIRUSTOTAL_API_KEY:
        return {}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f"https://www.virustotal.com/api/v3/domains/{domain}",
                headers={"x-apikey": settings.VIRUSTOTAL_API_KEY},
            )
            if r.status_code == 200:
                data = r.json()
                attrs = data.get("data", {}).get("attributes", {})
                return {
                    "last_analysis_stats": attrs.get("last_analysis_stats", {}),
                    "reputation": attrs.get("reputation"),
                    "tags": attrs.get("tags", []),
                    "registrar": attrs.get("registrar"),
                    "creation_date": attrs.get("creation_date"),
                }
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def _query_virustotal_hash(hash_value: str) -> Dict:
    if not settings.VIRUSTOTAL_API_KEY:
        return {}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f"https://www.virustotal.com/api/v3/files/{hash_value}",
                headers={"x-apikey": settings.VIRUSTOTAL_API_KEY},
            )
            if r.status_code == 200:
                data = r.json()
                attrs = data.get("data", {}).get("attributes", {})
                return {
                    "last_analysis_stats": attrs.get("last_analysis_stats", {}),
                    "reputation": attrs.get("reputation"),
                    "tags": attrs.get("tags", []),
                    "meaningful_name": attrs.get("meaningful_name"),
                    "type_description": attrs.get("type_description"),
                    "size": attrs.get("size"),
                    "first_submission_date": attrs.get("first_submission_date"),
                }
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def _query_virustotal_url(url: str) -> Dict:
    if not settings.VIRUSTOTAL_API_KEY:
        return {}
    try:
        import base64 as _b64
        url_id = _b64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f"https://www.virustotal.com/api/v3/urls/{url_id}",
                headers={"x-apikey": settings.VIRUSTOTAL_API_KEY},
            )
            if r.status_code == 200:
                data = r.json()
                attrs = data.get("data", {}).get("attributes", {})
                return {
                    "last_analysis_stats": attrs.get("last_analysis_stats", {}),
                    "reputation": attrs.get("reputation"),
                    "tags": attrs.get("tags", []),
                    "last_http_response_code": attrs.get("last_http_response_code"),
                    "url": attrs.get("url"),
                }
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def _query_circl_cve(cve_id: str) -> Dict:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
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
    except Exception:
        return {"error": "source unavailable"}


async def _query_email_dns(email: str) -> Dict:
    try:
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
    except Exception:
        return {"error": "source unavailable"}


async def _query_hunter_email(email: str) -> Dict:
    if not settings.HUNTER_IO_KEY:
        return {}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                "https://api.hunter.io/v2/email-verifier",
                params={"email": email, "api_key": settings.HUNTER_IO_KEY},
            )
            if r.status_code == 200:
                return r.json().get("data", {})
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def _query_ripe_asn(asn_num: str) -> Dict:
    try:
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
    except Exception:
        return {"error": "source unavailable"}


async def _query_ipinfo_asn(asn_num: str) -> Dict:
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


# ─────────────────────────────────────────────
# FEED FETCHERS (used by Celery beat tasks)
# ─────────────────────────────────────────────

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
