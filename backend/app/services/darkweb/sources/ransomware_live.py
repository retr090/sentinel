import asyncio
import re
import httpx
from datetime import datetime
from typing import List, Dict, Any, Tuple

BASE_URL = "https://api.ransomware.live/v2"

# Exact-match country codes checked only against the country field.
_COUNTRY_IDS = frozenset({"LK", "LKA", "SRI LANKA", "SRI_LANKA"})

# Substring suffixes checked only against website/URL fields.
_DOMAIN_SUFFIXES = (".lk", "gov.lk", "mil.lk", "ac.lk", "edu.lk")

# Checked against victim name + country only (not full description) with word boundaries.
# Keeps uniquely Sri Lankan terms; removes generic English words that cause false positives.
_NAME_PATTERNS = re.compile(
    r"\b("
    r"sri\s+lanka|srilanka|ceylon"
    r"|colombo|kandy|jaffna|galle|negombo|trincomalee|batticaloa"
    r"|cbsl"           # Central Bank of Sri Lanka acronym
    r"|slpa"           # Sri Lanka Ports Authority
    r"|mobitel"        # Sri Lanka-specific telco brand
    r"|bank\s+of\s+ceylon"
    r"|peoples\s+bank"  # Sri Lanka state bank (full phrase, not just "bank")
    r")\b",
    re.IGNORECASE,
)

_HEADERS = {
    "User-Agent": "SENTINEL-OSINT/1.0",
    "Accept": "application/json",
}
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def is_sri_lanka_related(
    victim: Dict[str, Any]
) -> Tuple[bool, str]:
    """Return (is_related, matched_keyword).

    Three independent checks, each scoped to the fields where a match is meaningful:
    1. Country field exact match — catches country-coded LK victims.
    2. Domain suffix match (website/url only) — catches .lk domains.
    3. Word-boundary regex on victim name + country — catches named Sri Lankan
       entities without false-positiving on generic English words in descriptions.
    """
    country = str(victim.get("country", "")).strip().upper()
    if country in _COUNTRY_IDS:
        return True, "country:LK"

    for url_field in ("website", "url", "domain"):
        domain = str(victim.get(url_field, "")).lower()
        if domain and any(domain.endswith(s) or f"/{s}" in domain or s in domain for s in _DOMAIN_SUFFIXES):
            return True, f"domain:{url_field}"

    # Only check name-like fields — NOT full description text (too noisy).
    name_text = " ".join(
        str(victim.get(f, ""))
        for f in ("victim", "name", "country")
        if victim.get(f)
    )
    m = _NAME_PATTERNS.search(name_text)
    if m:
        return True, m.group(0).lower()

    return False, ""


def calculate_severity(
    victim: Dict[str, Any],
    is_lk: bool,
    keyword: str,
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
    published = _parse_date(victim.get("published") or victim.get("date") or victim.get("attackdate"))

    title = f"[{group.upper()}] {victim_name}{f' ({country})' if country else ''}"

    snippet_parts = []
    if country:
        snippet_parts.append(f"Country: {country}")
    if website:
        snippet_parts.append(f"Website: {website}")
    if description:
        snippet_parts.append(description[:300])
    snippet = " | ".join(snippet_parts)

    severity = calculate_severity(victim, is_lk, keyword_matched)

    return {
        "keyword_matched": keyword_matched or "ransomware_monitor",
        "source": "ransomware_live",
        "source_url": website or f"https://ransomware.live/#victim={victim_name}",
        "title": title,
        "snippet": snippet[:500],
        "full_content": description,
        "severity": severity,
        "category": "ransomware",
        "threat_actor": group,
        "victim_org": victim_name,
        "victim_country": country,
        "published_at": published,
        "raw_data": victim,
    }


async def fetch_recent_victims(days: int = 7) -> List[Dict]:
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=True, headers=_HEADERS
        ) as client:
            r = await client.get(f"{BASE_URL}/recentvictims")
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        print(f"[ransomware.live] fetch_recent_victims error: {e}")
    return []


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


async def fetch_all_groups() -> List[Dict]:
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=True, headers=_HEADERS
        ) as client:
            r = await client.get(f"{BASE_URL}/groups")
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        print(f"[ransomware.live] fetch_all_groups error: {e}")
    return []


async def fetch_all_historical_lk() -> List[Dict]:
    """Fetch ALL historical Sri Lanka ransomware victims by scanning per-year endpoints.

    Scans /v2/victims/{year} for every year since 2021, plus the recent feed.
    Rate-limits between requests to avoid 429s. Returns deduplicated LK-only hits.
    """
    all_lk: List[Dict] = []
    seen_titles: set = set()

    def _title(v: Dict) -> str:
        group = v.get("group_name") or v.get("group") or "Unknown"
        name = v.get("victim") or v.get("name") or "Unknown"
        country = v.get("country", "")
        return f"[{group.upper()}] {name}{f' ({country})' if country else ''}"

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True, headers=_HEADERS) as client:
        current_year = datetime.utcnow().year
        for year in range(2021, current_year + 1):
            print(f"[historical] Fetching {year} victims...")
            retries = 0
            while retries < 3:
                try:
                    r = await client.get(f"{BASE_URL}/victims/{year}")
                    if r.status_code == 429:
                        wait = 15 * (retries + 1)
                        print(f"[historical] Rate limited on {year}, waiting {wait}s...")
                        await asyncio.sleep(wait)
                        retries += 1
                        continue
                    if r.status_code != 200 or r.text.strip().startswith("<"):
                        print(f"[historical] {year}: non-JSON response (status={r.status_code})")
                        break
                    victims = r.json()
                    if not isinstance(victims, list):
                        print(f"[historical] {year}: unexpected type {type(victims)}")
                        break
                    lk_count = 0
                    for v in victims:
                        is_lk, keyword = is_sri_lanka_related(v)
                        if is_lk:
                            t = _title(v)
                            if t not in seen_titles:
                                seen_titles.add(t)
                                v["_match_type"] = keyword
                                all_lk.append(v)
                                lk_count += 1
                                print(f"  ⚠ SL HIT [{year}]: {v.get('victim','?')} [{v.get('group','?')}] — {keyword}")
                    print(f"[historical] {year}: {len(victims)} scanned, {lk_count} SL hits")
                    break
                except Exception as e:
                    print(f"[historical] {year} error: {e}")
                    break
            await asyncio.sleep(2)

        # Also sweep recent feed for anything very new
        print("[historical] Checking recent victims feed...")
        try:
            r = await client.get(f"{BASE_URL}/recentvictims")
            if r.status_code == 200 and not r.text.strip().startswith("<"):
                for v in r.json():
                    is_lk, keyword = is_sri_lanka_related(v)
                    if is_lk:
                        t = _title(v)
                        if t not in seen_titles:
                            seen_titles.add(t)
                            v["_match_type"] = keyword
                            all_lk.append(v)
                            print(f"  ⚠ SL HIT [recent]: {v.get('victim','?')} — {keyword}")
        except Exception as e:
            print(f"[historical] recent feed error: {e}")

    print(f"[historical] Total unique SL victims: {len(all_lk)}")
    return all_lk
