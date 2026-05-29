import hashlib
import httpx
from datetime import datetime
from typing import List, Dict, Any

BASE_URL = "https://api.ransomware.live/v2"

_HEADERS = {
    "User-Agent": "SENTINEL-OSINT/1.0",
    "Accept": "application/json",
}
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

def calculate_severity(
    victim: Dict[str, Any],
    is_lk: bool,
) -> str:
    country = str(victim.get("country", "")).upper()
    website = str(victim.get("website", "")).lower()

    if country in ("LK", "LKA") or "gov.lk" in website or "mil.lk" in website:
        return "CRITICAL"

    if is_lk:
        return "HIGH"

    regional = ["india", "pakistan", "bangladesh", "myanmar", "nepal", "maldives", "afghanistan"]
    if any(r in str(victim.get("country", "")).lower() for r in regional):
        return "MEDIUM"

    return "LOW"


def _parse_date(date_str: Any) -> datetime | None:
    if not date_str:
        return None
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            return datetime.strptime(str(date_str)[:19], fmt[:19])
        except ValueError:
            continue
    return None


def _feed_posted_at(victim: Dict[str, Any]) -> datetime | None:
    for key in ("published", "published_at", "posted_at", "post_date", "date", "attackdate"):
        parsed = _parse_date(victim.get(key))
        if parsed:
            return parsed
    return None


def parse_victim(
    victim: Dict[str, Any],
    is_lk: bool = False,
    keyword_matched: str = "",
) -> Dict[str, Any]:
    group = victim.get("group_name") or victim.get("group") or "Unknown"
    victim_name = victim.get("victim") or victim.get("name") or "Unknown"
    country = victim.get("country", "")
    website = victim.get("website") or victim.get("url") or ""
    description = victim.get("description", "")
    published = _feed_posted_at(victim)

    title = f"[{group.upper()}] {victim_name}{f' ({country})' if country else ''}"

    snippet_parts = []
    if country:
        snippet_parts.append(f"Country: {country}")
    if website:
        snippet_parts.append(f"Website: {website}")
    if description:
        snippet_parts.append(description[:300])
    snippet = " | ".join(snippet_parts)

    severity = calculate_severity(victim, is_lk)
    dedup_hash = hashlib.sha256(
        f"ransomware_live|{group.strip().lower()}|{victim_name.strip().lower()}".encode("utf-8", errors="ignore")
    ).hexdigest()

    return {
        "keyword_matched": keyword_matched or "ransomware_monitor",
        "source": "ransomware_live",
        "source_url": website or f"https://ransomware.live/#victim={victim_name}",
        "title": title,
        "snippet": snippet[:500],
        "full_content": description,
        "severity": severity,
        "dedup_hash": dedup_hash,
        "category": "ransomware",
        "threat_actor": group,
        "victim_org": victim_name,
        "victim_country": country,
        "feed_posted_at": published or datetime.utcnow(),
        "published_at": published,
        "raw_data": victim,
    }


async def fetch_victims_by_country(country_code: str = "LK") -> List[Dict]:
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=True, headers=_HEADERS
        ) as client:
            r = await client.get(f"{BASE_URL}/victims/{country_code}")
            if r.status_code in (200,):
                return r.json()
    except Exception as e:
        print(f"[ransomware.live] fetch_victims_by_country error: {e}")
    return []
