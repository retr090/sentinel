import hashlib
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any

RSS_URL = "https://ransomware.live/rss"

_HEADERS = {
    "User-Agent": "SENTINEL-OSINT/1.0",
}
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def calculate_severity(victim: Dict[str, Any], is_lk: bool) -> str:
    country = str(victim.get("victim_country", "")).upper()

    if country in ("LK", "LKA"):
        return "CRITICAL"

    if is_lk:
        return "HIGH"

    regional = ["india", "pakistan", "bangladesh", "myanmar", "nepal", "maldives", "afghanistan"]
    if any(r in country.lower() for r in regional):
        return "MEDIUM"

    return "LOW"


def _parse_rss_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None) - dt.utcoffset()
            return dt
        except ValueError:
            continue
    return None


def _parse_victim_from_rss(item: ET.Element) -> Dict[str, Any]:
    title_el = item.find("title")
    link_el = item.find("link")
    desc_el = item.find("description")
    category_el = item.find("category")
    pubdate_el = item.find("pubDate")

    title = title_el.text if title_el is not None else ""
    link = link_el.text if link_el is not None else ""
    description = desc_el.text if desc_el is not None else ""
    country_code = category_el.text if category_el is not None else ""
    pub_date_str = pubdate_el.text if pubdate_el is not None else ""

    published = _parse_rss_date(pub_date_str)

    group = "Unknown"
    victim_name = title
    if "has just published a new victim :" in title:
        parts = title.split("has just published a new victim :", 1)
        group = parts[0].replace("🏴\u200d☠️", "").strip()
        victim_name = parts[1].strip() if len(parts) > 1 else "Unknown"

    dedup_hash = hashlib.sha256(
        f"ransomware_live|{group.strip().lower()}|{victim_name.strip().lower()}".encode("utf-8", errors="ignore")
    ).hexdigest()

    return {
        "keyword_matched": "country:" + country_code if country_code else "ransomware_monitor",
        "source": "ransomware_live",
        "source_url": link or f"https://ransomware.live/",
        "title": title,
        "snippet": (description[:300] if description else ""),
        "full_content": description or "",
        "severity": "LOW",
        "dedup_hash": dedup_hash,
        "category": "ransomware",
        "threat_actor": group,
        "victim_org": victim_name,
        "victim_country": country_code,
        "feed_posted_at": published or datetime.utcnow(),
        "published_at": published,
        "raw_data": {
            "title": title,
            "link": link,
            "description": description,
            "category": country_code,
            "pub_date": pub_date_str,
        },
    }


async def fetch_victims_by_country(country_code: str = "LK") -> List[Dict]:
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=True, headers=_HEADERS
        ) as client:
            r = await client.get(RSS_URL)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                victims = []
                for item in root.findall(".//item"):
                    victim = _parse_victim_from_rss(item)
                    victim["severity"] = calculate_severity(victim, country_code.upper() in ("LK", "LKA"))
                    if country_code.upper() in ("ALL", ""):
                        victims.append(victim)
                    elif victim.get("victim_country", "").upper() == country_code.upper():
                        victims.append(victim)
                return victims
    except Exception as e:
        print(f"[ransomware.live] fetch_victims_by_country error: {e}")
    return []


def parse_victim(
    victim: Dict[str, Any],
    is_lk: bool = False,
    keyword_matched: str = "",
) -> Dict[str, Any]:
    if "dedup_hash" in victim:
        return victim
    group = victim.get("group_name") or victim.get("group") or "Unknown"
    victim_name = victim.get("victim") or victim.get("name") or "Unknown"
    country = victim.get("country", "")
    website = victim.get("website") or victim.get("url") or ""
    description = victim.get("description", "")
    published = _parse_rss_date(str(victim.get("published", "")))

    title = f"[{group.upper()}] {victim_name}{f' ({country})' if country else ''}"

    snippet_parts = []
    if country:
        snippet_parts.append(f"Country: {country}")
    if website:
        snippet_parts.append(f"Website: {website}")
    if description:
        snippet_parts.append(description[:300])
    snippet = " | ".join(snippet_parts)

    severity = calculate_severity({"victim_country": country}, is_lk)
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
