import httpx
from app.core.config import settings

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def lookup(ip: str) -> dict:
    if not settings.ABUSEIPDB_API_KEY:
        return {"error": "no_api_key"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                "https://api.abuseipdb.com/api/v2/check",
                headers={
                    "Key": settings.ABUSEIPDB_API_KEY,
                    "Accept": "application/json",
                },
                params={
                    "ipAddress": ip,
                    "maxAgeInDays": 90,
                    "verbose": True,
                },
            )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}
            data = r.json().get("data", {})
            return {
                "ip_address": data.get("ipAddress"),
                "is_public": data.get("isPublic"),
                "abuse_confidence_score": data.get("abuseConfidenceScore", 0),
                "country_code": data.get("countryCode"),
                "usage_type": data.get("usageType"),
                "isp": data.get("isp"),
                "domain": data.get("domain"),
                "is_whitelisted": data.get("isWhitelisted"),
                "total_reports": data.get("totalReports", 0),
                "num_distinct_users": data.get("numDistinctUsers", 0),
                "last_reported_at": data.get("lastReportedAt"),
                "reports": data.get("reports", [])[:5],
            }
    except Exception as e:
        return {"error": str(e)}
