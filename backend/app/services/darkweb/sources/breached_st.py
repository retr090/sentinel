"""
Breached.st / BreachForums scanner (XenForo software).

Searches ONLY the Leaks category (node 12, which includes children:
  14=Databases, 54=Official Database Section, 15=Stealer Logs,
  16=Other Leaks, 17=Database Discussion)
and filters results to Sri Lanka related content.

Requires authenticated session cookies obtained via forum_auth.auto_login_forum.
"""
import re
import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Dict, List

BASE_URL = "https://breached.st"
SEARCH_URL = f"{BASE_URL}/search/search"

# Leaks category node ID — parent of Databases, Other Leaks, Stealer Logs, etc.
LEAKS_NODE_ID = "12"

# Leaks sub-forum node IDs for browse fallback
LEAKS_SUBNODES = ["14", "54", "15", "16"]  # Databases, Official DB, Stealer Logs, Other Leaks

# Forums considered part of the Leaks/data family (for snippet-level matching)
LEAKS_CATEGORIES = {
    "databases", "official database section", "stealer logs",
    "other leaks", "database discussion", "sellers place",
}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL,
}


# Words that signal actual compromised/leaked data being shared.
# Must match at least one to be included — filters out news, defacement reports,
# and general discussion threads that mention SL keywords without containing real data.
DATA_INDICATORS = frozenset({
    # Data exposure
    "database", "db dump", "data dump", "dump", "leaked", "leak", "leaks",
    "breach", "breached", "exposed", "compromised",
    # Credential / PII content
    "credentials", "passwords", "usernames", "combolist", "combo",
    "fullz", "ssn", "passport", "id card", "national id",
    "email list", "phone list", "user data", "customer data", "personal info", "pii",
    # Data artefacts
    "records", "rows", "sql", "mysql", "backup", "dataset", "collection", "archive",
    "stealer", "stealer logs",
    # Sale / access listings
    "for sale", "selling", "free download", "download link",
    "rdp", "vpn access", "shell access", "admin access",
})

# Patterns that strongly indicate a news/discussion thread rather than a data post.
# Checked against the title only (snippets can legitimately contain these words).
NEWS_TITLE_PATTERNS = (
    "breaking:", "[news]", "news:", "discussion:", "[discussion]",
    "allegedly", "report:", "warning:", "advisory",
    "cyber attack on", "ddos attack", "defaced", "defacement",
    "hacking group claims", "claims to have hacked",
)


def _is_data_post(title: str, snippet: str) -> bool:
    """Return True only if the thread contains evidence of actual compromised data.

    Requires at least one DATA_INDICATOR in title+snippet, and no strong news-title
    pattern that marks it as a news/discussion thread rather than a data leak post.
    """
    title_lower = title.lower()
    # Reject up-front if the title looks like a news headline
    if any(p in title_lower for p in NEWS_TITLE_PATTERNS):
        return False
    combined = title_lower + " " + snippet.lower()
    return any(ind in combined for ind in DATA_INDICATORS)


def determine_severity(title: str, snippet: str) -> str:
    text = (title + " " + snippet).lower()
    if any(t in text for t in [
        "gov.lk", "mil.lk", "military", "air force", "navy", "army",
        "police.lk", "ministry", "parliament", "central bank", "cbsl",
        "government database", "defense", "defence", "missing persons",
        "provincial council",
    ]):
        return "CRITICAL"
    if any(t in text for t in [
        "database", "dump", "leaked", "breach", "credentials", "passwords",
        "bank", "telecom", "electricity", "airport", "hospital", "fullz",
        "ssn", "passport", "id card", "customer data", "user data",
        "email list", "phone number", "personal info", "stealer",
    ]):
        return "HIGH"
    return "MEDIUM"


def _strip_post_anchor(href: str) -> str:
    """Convert /threads/slug.123/post-456 to /threads/slug.123/"""
    return re.sub(r"/post-\d+$", "/", href)


def _parse_result_item(item, keyword: str) -> Dict:
    """Extract structured data from a XenForo search result <li>."""
    try:
        author = item.get("data-author", "")

        title_el = item.find("h3", class_=re.compile(r"contentRow-title", re.I))
        link = title_el.find("a") if title_el else None
        if not link:
            return {}

        title = link.get_text(strip=True)
        href = link.get("href", "")
        if href and not href.startswith("http"):
            href = f"{BASE_URL}/{href.lstrip('/')}"
        thread_url = _strip_post_anchor(href)

        snippet_el = item.find(class_=re.compile(r"contentRow-snippet", re.I))
        snippet = snippet_el.get_text(strip=True)[:400] if snippet_el else ""

        time_el = item.find("time")
        published_at = None
        if time_el:
            ts = time_el.get("data-timestamp")
            if ts:
                try:
                    published_at = datetime.utcfromtimestamp(int(ts))
                except (ValueError, TypeError):
                    pass

        forum_el = item.find("a", href=re.compile(r"/forums/", re.I))
        forum_name = forum_el.get_text(strip=True) if forum_el else "Leaks"

        if not title:
            return {}

        title_lower = title.lower()
        kw_lower = keyword.lower()
        kw_nospace = kw_lower.replace(" ", "")   # "sri lanka" → "srilanka"
        cat_lower = forum_name.lower()
        # Match either spaced or unspaced form — forum titles often omit spaces
        # e.g. "SriLanka" matches keyword "sri lanka"
        title_has_kw = kw_lower in title_lower or kw_nospace in title_lower.replace(" ", "")
        snippet_lower = snippet.lower()
        snippet_has_kw = kw_lower in snippet_lower or kw_nospace in snippet_lower.replace(" ", "")
        in_leaks_forum = cat_lower in LEAKS_CATEGORIES

        # Keep result if the search keyword appears directly in the title.
        # If it only appears in the snippet (search engine matched it in the post body),
        # require the title itself to also carry a data indicator — blocks unrelated
        # threads that mention the keyword only in passing.
        if title_has_kw:
            pass
        elif snippet_has_kw and in_leaks_forum:
            if not _is_data_post(title, ""):
                return {}
        else:
            return {}

        # Reject news/discussion threads — only keep posts that contain evidence
        # of actual compromised/leaked data (not just mentions of SL keywords)
        if not _is_data_post(title, snippet):
            return {}

        return {
            "title": title[:500],
            "url": thread_url[:2000],
            "source_url": thread_url[:2000],
            "snippet": snippet,
            "author": author,
            "published_at": published_at,
            "keyword_matched": keyword,
            "forum_id": "breached_st",
            "forum_name": "Breached.st",
            "category": forum_name or "Leaks",
            "severity": determine_severity(title, snippet),
            "source": "breached_st",
            "discovered_at": datetime.utcnow().isoformat(),
        }
    except Exception:
        return {}


async def check_session_valid(cookies: Dict[str, str]) -> bool:
    """Return True if the current session cookies grant authenticated access."""
    if not cookies.get("xf_user"):
        return False
    try:
        async with httpx.AsyncClient(
            timeout=15, follow_redirects=True, headers=BROWSER_HEADERS
        ) as client:
            r = await client.get(BASE_URL, cookies=cookies)
            if r.status_code != 200:
                return False
            if "/login" in str(r.url) and str(r.url).rstrip("/") != BASE_URL:
                return False
            return 'data-logged-in="true"' in r.text
    except Exception:
        return False


async def _get_xf_token(client: httpx.AsyncClient) -> str:
    """Fetch a fresh XenForo CSRF token."""
    try:
        r = await client.get(f"{BASE_URL}/search/")
        soup = BeautifulSoup(r.text, "html.parser")
        csrf = soup.find("html", {"data-csrf": True})
        if csrf:
            return csrf["data-csrf"]
        token_el = soup.find("input", {"name": "_xfToken"})
        return token_el.get("value", "") if token_el else ""
    except Exception:
        return ""


async def search_leaks_for_keyword(
    keyword: str,
    cookies: Dict[str, str],
    client: httpx.AsyncClient,
) -> List[Dict]:
    """
    POST search restricted to Leaks category (node 12 + child_nodes=1).
    Returns parsed result dicts deduplicated by thread URL.
    """
    results = []
    seen = set()

    try:
        token = await _get_xf_token(client)
        print(f"  Searching Leaks for: '{keyword}'")

        sr = await client.post(
            SEARCH_URL,
            data={
                "keywords": keyword,
                "users": "",
                "date": "",
                "child_nodes": "1",
                "type": "post",
                "order": "date",
                "nodes[]": LEAKS_NODE_ID,
                "_xfToken": token,
                "_xfRequestUri": "/search/",
            },
            headers={
                **BROWSER_HEADERS,
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": BASE_URL,
                "Referer": f"{BASE_URL}/search/",
            },
            timeout=30,
        )

        if sr.status_code != 200:
            print(f"  Search HTTP {sr.status_code} for '{keyword}'")
            return []

        if "/login" in str(sr.url):
            return [{"error": "session_expired"}]

        soup = BeautifulSoup(sr.text, "html.parser")
        items = soup.find_all("li", class_=re.compile(r"block-row", re.I))
        print(f"  Found {len(items)} raw items for '{keyword}'")

        for item in items[:30]:
            data = _parse_result_item(item, keyword)
            if not data:
                continue
            key = data.get("url") or data.get("title", "")
            if key and key not in seen:
                seen.add(key)
                results.append(data)

    except httpx.TimeoutException:
        print(f"  Timeout searching '{keyword}'")
    except Exception as e:
        print(f"  Error searching '{keyword}': {e}")

    return results


async def browse_leaks_for_keyword(
    keyword: str,
    cookies: Dict[str, str],
    client: httpx.AsyncClient,
    max_pages: int = 3,
) -> List[Dict]:
    """
    Browse Leaks sub-forum listing pages and filter thread titles by keyword.
    Used as fallback when search returns nothing.
    """
    results = []
    seen = set()

    for node_id in LEAKS_SUBNODES:
        for page in range(1, max_pages + 1):
            try:
                url = f"{BASE_URL}/forums/{node_id}/"
                params = {"page": str(page)} if page > 1 else {}
                r = await client.get(url, params=params, cookies=cookies, timeout=20)

                if r.status_code != 200:
                    break
                if "/login" in str(r.url):
                    return [{"error": "session_expired"}]

                soup = BeautifulSoup(r.text, "html.parser")
                thread_rows = soup.find_all(
                    "div", class_=re.compile(r"structItem--thread", re.I)
                ) or soup.find_all("li", class_=re.compile(r"discussionListItem", re.I))

                if not thread_rows:
                    break

                page_hits = 0
                kw_lower = keyword.lower()
                kw_nospace = kw_lower.replace(" ", "")
                for row in thread_rows:
                    row_text = row.get_text().lower()
                    if kw_lower not in row_text and kw_nospace not in row_text.replace(" ", ""):
                        continue
                    matched_kw = keyword

                    link = row.find("a", href=re.compile(r"/threads/"))
                    if not link:
                        continue

                    title = link.get_text(strip=True)
                    href = link.get("href", "")
                    if href and not href.startswith("http"):
                        href = f"{BASE_URL}/{href.lstrip('/')}"
                    thread_url = _strip_post_anchor(href)

                    if thread_url in seen:
                        continue

                    # Only include threads with actual data indicators
                    if not _is_data_post(title, ""):
                        continue

                    seen.add(thread_url)

                    data = {
                        "title": title[:500],
                        "url": thread_url[:2000],
                        "snippet": "",
                        "author": row.get("data-author", ""),
                        "date_posted": "",
                        "keyword_matched": matched_kw,
                        "forum_id": "breached_st",
                        "forum_name": "Breached.st",
                        "category": "Leaks",
                        "severity": determine_severity(title, ""),
                        "source": "breached_st",
                        "discovered_at": datetime.utcnow().isoformat(),
                    }
                    results.append(data)
                    page_hits += 1

                print(f"  Node {node_id} page {page}: {page_hits} SL hits")
                if page_hits == 0 and page > 1:
                    break

                await asyncio.sleep(2)

            except Exception as e:
                print(f"  Browse node {node_id} page {page} error: {e}")
                break

    return results


async def run_full_scan(
    cookies: Dict[str, str],
    keywords: List[str] = None,
) -> List[Dict]:
    """
    Scan Breached.st Leaks category for Sri Lanka related content.

    Strategy:
      1. Verify session is still valid.
      2. POST-search each SL keyword restricted to node 12 (Leaks + children).
      3. If search yields nothing, browse Leaks sub-forum pages directly.
      4. Deduplicate all results by thread URL.
    """
    active_keywords = keywords or []
    if not active_keywords:
        print("No keywords provided — skipping scan")
        return []

    print("Verifying Breached.st session...")
    if not await check_session_valid(cookies):
        print("Session invalid — need re-login")
        return [{
            "error": "session_expired",
            "forum": "breached_st",
            "message": "Breached.st session expired. Auto-login will retry.",
        }]

    print(f"Session valid — scanning Leaks category (node {LEAKS_NODE_ID})...")

    all_results: List[Dict] = []
    seen_urls: set = set()

    async with httpx.AsyncClient(
        timeout=30, follow_redirects=True, headers=BROWSER_HEADERS, cookies=cookies
    ) as client:
        # Phase 1: keyword search restricted to Leaks node
        for keyword in active_keywords:
            hits = await search_leaks_for_keyword(keyword, cookies, client)

            if any(h.get("error") == "session_expired" for h in hits):
                print("Session expired mid-scan")
                return [{"error": "session_expired"}]

            for h in hits:
                if h.get("error"):
                    continue
                key = h.get("url") or h.get("title", "")
                if key and key not in seen_urls:
                    seen_urls.add(key)
                    all_results.append(h)

            await asyncio.sleep(3)

        # Phase 2: browse fallback if search returned nothing
        if not all_results:
            print("Search returned nothing — browsing Leaks sub-forums...")
            for keyword in active_keywords:
                browse_hits = await browse_leaks_for_keyword(keyword, cookies, client)
                for h in browse_hits:
                    if h.get("error"):
                        continue
                    key = h.get("url") or h.get("title", "")
                    if key and key not in seen_urls:
                        seen_urls.add(key)
                        all_results.append(h)
                await asyncio.sleep(2)

    print(f"Breached.st Leaks scan complete: {len(all_results)} Sri Lanka results")
    for r in all_results:
        print(f"  [{r.get('severity', '?')}] {r.get('title', '')[:70]}")

    return all_results
