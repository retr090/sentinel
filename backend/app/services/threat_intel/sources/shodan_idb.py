import httpx
from app.core.config import settings

TIMEOUT = httpx.Timeout(15.0, connect=5.0)
_API = "https://api.shodan.io"
_IDB = "https://internetdb.shodan.io"


async def lookup(ip: str) -> dict:
    """Full host lookup — uses Shodan API if key available, else InternetDB."""
    if settings.SHODAN_API_KEY:
        return await _lookup_full(ip)
    return await _lookup_internetdb(ip)


async def _lookup_full(ip: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f"{_API}/shodan/host/{ip}",
                params={"key": settings.SHODAN_API_KEY},
            )
            if r.status_code == 200:
                return _normalize_host(r.json())
            if r.status_code == 404:
                return {"error": "No information available for that IP."}
        return await _lookup_internetdb(ip)
    except Exception:
        return await _lookup_internetdb(ip)


def _normalize_host(data: dict) -> dict:
    services = []
    for item in data.get("data", []):
        svc: dict = {
            "port": item.get("port"),
            "transport": item.get("transport", "tcp"),
            "product": item.get("product"),
            "version": item.get("version"),
            "cpe": item.get("cpe") or [],
            "banner": (item.get("data") or "")[:500],
        }
        if item.get("http"):
            svc["http"] = {
                "title": item["http"].get("title"),
                "server": item["http"].get("server"),
                "status": item["http"].get("status"),
            }
        if item.get("ssl"):
            svc["ssl"] = {
                "subject": (item["ssl"].get("subject") or {}).get("CN"),
                "expires": (item["ssl"].get("cert") or {}).get("expires"),
                "version": item["ssl"].get("version"),
            }
        services.append(svc)

    raw_vulns = data.get("vulns") or {}
    vuln_list = []
    if isinstance(raw_vulns, dict):
        for cve_id, vdata in raw_vulns.items():
            vuln_list.append({
                "cve": cve_id,
                "cvss": vdata.get("cvss"),
                "summary": (vdata.get("summary") or "")[:300],
                "references": (vdata.get("references") or [])[:3],
            })
    elif isinstance(raw_vulns, list):
        vuln_list = [{"cve": v} for v in raw_vulns]
    vuln_list.sort(key=lambda v: v.get("cvss") or 0, reverse=True)

    all_cpes = list({cpe for svc in data.get("data", []) for cpe in (svc.get("cpe") or [])})

    return {
        "ip": data.get("ip_str"),
        "hostnames": data.get("hostnames") or [],
        "domains": data.get("domains") or [],
        "ports": data.get("ports") or [],
        "os": data.get("os"),
        "org": data.get("org"),
        "isp": data.get("isp"),
        "asn": data.get("asn"),
        "country": data.get("country_name"),
        "city": data.get("city"),
        "region": data.get("region_code"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "tags": data.get("tags") or [],
        "cpes": all_cpes,
        "vulns": vuln_list,
        "services": services,
        "last_update": data.get("last_update"),
        "_source": "shodan_api",
    }


async def _lookup_internetdb(ip: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{_IDB}/{ip}")
            if r.status_code == 200:
                result = r.json()
                result["_source"] = "internetdb"
                return result
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def search(query: str, page: int = 1, facets: str = "") -> dict:
    """Search Shodan for matching hosts. Requires API key."""
    if not settings.SHODAN_API_KEY:
        return {"error": "Shodan API key not configured"}
    try:
        params: dict = {"key": settings.SHODAN_API_KEY, "query": query, "page": page}
        if facets:
            params["facets"] = facets
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{_API}/shodan/host/search", params=params)
            if r.status_code == 200:
                data = r.json()
                matches = []
                for m in data.get("matches", []):
                    matches.append({
                        "ip": m.get("ip_str"),
                        "port": m.get("port"),
                        "transport": m.get("transport"),
                        "product": m.get("product"),
                        "version": m.get("version"),
                        "org": m.get("org"),
                        "isp": m.get("isp"),
                        "asn": m.get("asn"),
                        "country": (m.get("location") or {}).get("country_name"),
                        "city": (m.get("location") or {}).get("city"),
                        "hostnames": m.get("hostnames") or [],
                        "domains": m.get("domains") or [],
                        "timestamp": m.get("timestamp"),
                        "banner": (m.get("data") or "")[:300],
                        "vulns": list((m.get("vulns") or {}).keys()),
                        "tags": m.get("tags") or [],
                    })
                return {
                    "total": data.get("total", 0),
                    "page": page,
                    "matches": matches,
                    "facets": data.get("facets", {}),
                }
            if r.status_code == 401:
                return {"error": "Invalid Shodan API key"}
            return {"error": f"Shodan returned HTTP {r.status_code}"}
    except Exception:
        return {"error": "source unavailable"}


async def count(query: str) -> dict:
    """Count matching hosts without consuming query credits."""
    if not settings.SHODAN_API_KEY:
        return {"error": "Shodan API key not configured"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f"{_API}/shodan/host/count",
                params={"key": settings.SHODAN_API_KEY, "query": query},
            )
            if r.status_code == 200:
                return r.json()
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def lookup_domain(domain: str) -> dict:
    """Shodan DNS data — subdomains, IPs, record types. Requires API key."""
    if not settings.SHODAN_API_KEY:
        return {}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f"{_API}/dns/domain/{domain}",
                params={"key": settings.SHODAN_API_KEY},
            )
            if r.status_code == 200:
                data = r.json()
                return {
                    "domain": data.get("domain"),
                    "subdomains": data.get("subdomains") or [],
                    "tags": data.get("tags") or [],
                    "records": [
                        {
                            "subdomain": rec.get("subdomain"),
                            "type": rec.get("type"),
                            "value": rec.get("value"),
                            "last_seen": rec.get("last_seen"),
                        }
                        for rec in (data.get("data") or [])[:50]
                    ],
                }
        return {}
    except Exception:
        return {"error": "source unavailable"}


async def api_info() -> dict:
    """Return account info — useful for verifying the key and checking credits."""
    if not settings.SHODAN_API_KEY:
        return {"error": "Shodan API key not configured"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{_API}/api-info", params={"key": settings.SHODAN_API_KEY})
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401:
                return {"error": "Invalid API key"}
        return {}
    except Exception:
        return {"error": "source unavailable"}
