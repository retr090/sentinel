import re
import httpx
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from urllib.parse import urlsplit

from ..encryption import decrypt_password

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


async def login_mybb(
    base_url: str,
    username: str,
    password: str,
    login_url: str = None,
) -> Tuple[bool, Dict[str, str], str]:
    """Login to a MyBB forum. Returns (success, cookies, error)."""
    parsed = urlsplit(base_url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    member_url = f"{domain}/member.php"

    try:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers=BROWSER_HEADERS,
        ) as client:
            get_r = await client.get(member_url, params={"action": "login"})
            if get_r.status_code != 200:
                return False, {}, f"Login page returned HTTP {get_r.status_code}"

            soup = BeautifulSoup(get_r.text, "html.parser")
            login_form = (
                soup.find("form", {"action": re.compile(r"member\.php", re.I)})
                or soup.find("form", {"id": re.compile(r"login", re.I)})
                or soup.find("form", {"class": re.compile(r"login", re.I)})
            )

            hidden_fields = {}
            if login_form:
                for inp in login_form.find_all("input", {"type": "hidden"}):
                    name = inp.get("name", "")
                    value = inp.get("value", "")
                    if name:
                        hidden_fields[name] = value

            login_data = {
                "action": "do_login",
                "username": username,
                "password": password,
                "remember": "yes",
                "submit": "Login",
                **hidden_fields,
            }

            post_r = await client.post(
                member_url,
                data=login_data,
            )

            all_cookies: Dict[str, str] = {}
            for resp in post_r.history:
                all_cookies.update(dict(resp.cookies))
            all_cookies.update(dict(post_r.cookies))

            page_text = post_r.text.lower()

            failed_indicators = [
                "incorrect username", "wrong password", "invalid username",
                "login failed", "you have been banned",
            ]
            if any(ind in page_text for ind in failed_indicators):
                return False, {}, "Login failed — incorrect username or password"

            if "mybbuser" in all_cookies:
                print(f"MyBB login successful — {len(all_cookies)} cookies")
                return True, all_cookies, ""

            verify_r = await client.get(f"{domain}/usercp.php", cookies=all_cookies)
            if "usercp" in str(verify_r.url) and verify_r.status_code == 200:
                return True, all_cookies, ""

            return False, {}, "Login appeared to fail — no session cookies received"

    except httpx.TimeoutException:
        return False, {}, "Login timed out"
    except Exception as e:
        return False, {}, f"Login error: {e}"


async def login_phpbb(
    base_url: str,
    username: str,
    password: str,
) -> Tuple[bool, Dict[str, str], str]:
    """Login to a phpBB forum."""
    login_url = f"{base_url}/ucp.php"
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(login_url, params={"mode": "login"})
            soup = BeautifulSoup(r.text, "html.parser")

            sid = creation_time = form_token = ""
            for inp in soup.find_all("input", {"type": "hidden"}):
                name = inp.get("name", "")
                value = inp.get("value", "")
                if name == "sid":
                    sid = value
                elif name == "creation_time":
                    creation_time = value
                elif name == "form_token":
                    form_token = value

            post_r = await client.post(
                login_url,
                params={"mode": "login"},
                data={
                    "username": username,
                    "password": password,
                    "login": "Login",
                    "sid": sid,
                    "creation_time": creation_time,
                    "form_token": form_token,
                    "redirect": "./index.php",
                },
            )
            all_cookies = dict(post_r.cookies)
            if any("phpbb3_" in k for k in all_cookies):
                return True, all_cookies, ""
            return False, {}, "phpBB login failed"
    except Exception as e:
        return False, {}, str(e)


async def login_xenforo(
    base_url: str,
    username: str,
    password: str,
) -> Tuple[bool, Dict[str, str], str]:
    """Login to a XenForo forum (Breached.st, RaidForums etc.)."""
    try:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers=BROWSER_HEADERS,
        ) as client:
            # Step 1: load login page to get CSRF token + redirect value
            r = await client.get(f"{base_url}/login")
            if r.status_code != 200:
                return False, {}, f"Login page returned HTTP {r.status_code}"

            soup = BeautifulSoup(r.text, "html.parser")
            token_el = soup.find("input", {"name": "_xfToken"})
            token = token_el.get("value", "") if token_el else ""
            redirect_el = soup.find("input", {"name": "_xfRedirect"})
            redirect = redirect_el.get("value", f"{base_url}/") if redirect_el else f"{base_url}/"

            initial_cookies = dict(r.cookies)

            # Step 2: POST credentials
            post_r = await client.post(
                f"{base_url}/login/login",
                data={
                    "login": username,
                    "password": password,
                    "remember": "1",
                    "_xfToken": token,
                    "_xfRedirect": redirect,
                    "_xfResponseType": "html",
                },
                cookies=initial_cookies,
                headers={
                    **BROWSER_HEADERS,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": f"{base_url}/login",
                    "Origin": base_url,
                },
            )

            all_cookies: Dict[str, str] = {}
            for resp in post_r.history:
                all_cookies.update(dict(resp.cookies))
            all_cookies.update(dict(post_r.cookies))

            # XenForo sets xf_user on successful login
            if any("xf_" in k for k in all_cookies):
                # Verify it's actually the user cookie, not just a session cookie
                if "xf_user" in all_cookies or "data-logged-in=\"true\"" in post_r.text:
                    print(f"XenForo login successful — cookies: {list(all_cookies.keys())}")
                    return True, all_cookies, ""

            # Check page content for explicit failure messages
            page = post_r.text.lower()
            if "incorrect password" in page or "invalid credentials" in page:
                return False, {}, "Login failed — incorrect username or password"
            if "two-step" in page or "two_step" in page:
                return False, {}, "Login failed — two-step verification required"

            # If we got xf_session but not xf_user, login didn't fully authenticate
            if all_cookies:
                return False, {}, f"Login incomplete — got {list(all_cookies.keys())} but no xf_user"
            return False, {}, "XenForo login failed — no cookies returned"

    except httpx.TimeoutException:
        return False, {}, "Login timed out"
    except Exception as e:
        return False, {}, f"Login error: {e}"


async def auto_login_forum(
    forum_id: str,
    base_url: str,
    forum_software: str,
    username: str,
    encrypted_password: str,
    login_url: str = None,
) -> Tuple[bool, Dict[str, str], str]:
    """Dispatch login to the correct handler based on forum_software."""
    try:
        password = decrypt_password(encrypted_password)
    except Exception as e:
        return False, {}, f"Failed to decrypt password: {e}"

    software = (forum_software or "mybb").lower()

    if software == "phpbb":
        return await login_phpbb(base_url, username, password)
    elif software == "xenforo":
        return await login_xenforo(base_url, username, password)
    else:
        # mybb is the default (also covers "custom" and empty)
        return await login_mybb(base_url, username, password, login_url)


async def _check_mybb_session(cookies: Dict[str, str], base_url: str) -> bool:
    parsed = urlsplit(base_url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=BROWSER_HEADERS, cookies=cookies) as c:
            r = await c.get(f"{domain}/usercp.php")
            if r.status_code == 200 and "usercp" in str(r.url).lower():
                return True
    except Exception:
        pass
    return False


async def ensure_valid_session(forum, db) -> Tuple[bool, str]:
    software = (forum.forum_software or "mybb").lower()

    if forum.session_cookies:
        try:
            if software == "xenforo" or "breached" in (forum.forum_id or "").lower():
                from .sources.breached_st import check_session_valid
                is_valid = await check_session_valid(forum.session_cookies)
            else:
                is_valid = await _check_mybb_session(forum.session_cookies, base_url=forum.forum_url)
            if is_valid:
                return True, ""
        except Exception:
            pass

    if not forum.auto_login:
        return False, "Session expired and auto-login disabled"
    if not forum.encrypted_password:
        return False, "No password stored for auto-login"
    if not forum.username:
        return False, "No username stored for auto-login"

    if forum.last_login_attempt:
        elapsed = (datetime.utcnow() - forum.last_login_attempt).total_seconds()
        if elapsed < 300:
            remaining = int(300 - elapsed)
            return False, f"Login cooldown active — retry in {remaining}s"

    print(f"Auto-logging in to {forum.forum_name}...")
    forum.last_login_attempt = datetime.utcnow()
    forum.login_attempts = (forum.login_attempts or 0) + 1
    await db.commit()

    success, cookies, error = await auto_login_forum(
        forum_id=forum.forum_id,
        base_url=forum.forum_url,
        forum_software=forum.forum_software or "mybb",
        username=forum.username,
        encrypted_password=forum.encrypted_password,
        login_url=forum.login_url,
    )

    if success:
        forum.session_cookies = cookies
        forum.last_successful_login = datetime.utcnow()
        forum.session_valid_until = datetime.utcnow() + timedelta(days=7)
        await db.commit()
        print(f"Auto-login successful for {forum.forum_name}")
        return True, ""
    else:
        print(f"Auto-login failed for {forum.forum_name}: {error}")
        return False, error


def _mybb_determine_severity(title: str, snippet: str) -> str:
    text = (title + " " + snippet).lower()
    if any(w in text for w in ("leak", "breach", "dump", "crack", "exploit", "0day", "rce")):
        return "CRITICAL"
    if any(w in text for w in ("database", "sql", "admin", "password", "credential", "root", "shell")):
        return "HIGH"
    if any(w in text for w in ("access", "bypass", "backdoor", "vuln", "inject", "xss")):
        return "HIGH"
    return "MEDIUM"


def _parse_mybb_date(text: str) -> str:
    now = datetime.utcnow()
    text = text.strip().lower()
    if "minute" in text or "hour" in text or "second" in text:
        return now
    if "yesterday" in text:
        return now - timedelta(days=1)
    m = re.match(r"(\d{1,2})-(\d{1,2})-(\d{2,4}),?\s+(\d{1,2}:\d{2}\s*(?:am|pm))", text)
    if m:
        day, mon, yr, tm = m.groups()
        yr = int(yr)
        if yr < 100:
            yr += 2000
        try:
            return datetime.strptime(f"{yr}-{mon}-{day} {tm}", "%Y-%m-%d %I:%M %p")
        except ValueError:
            pass
    return now


async def search_mybb_forum(
    base_url: str,
    cookies: Dict[str, str],
    keywords: List[str],
    forum_name: str = "",
    forum_id: str = "",
) -> List[Dict]:
    results: List[Dict] = []
    seen_urls: set = set()

    async with httpx.AsyncClient(
        timeout=20, follow_redirects=True, headers=BROWSER_HEADERS, cookies=cookies
    ) as client:
        parsed = urlsplit(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        for keyword in keywords:
            try:
                r = await client.post(
                    f"{domain}/search.php",
                    data={"keywords": keyword, "action": "do_search", "postthread": "1", "showresults": "threads", "submit": "Search"},
                )
                if r.status_code not in (200, 302):
                    continue
                if "/login" in str(r.url) or "member.php" in str(r.url):
                    print(f"  MyBB session expired during search for '{keyword}'")
                    return [{"error": "session_expired"}]

                soup = BeautifulSoup(r.text, "html.parser")
                threads = soup.find_all("tr", class_=re.compile(r"inline_row|trow")) or soup.find_all("li", class_=re.compile(r"topic"))

                if not threads:
                    threads = soup.select("table.forum_threads tr, .threadbit tr, .forumbit tr")

                print(f"  MyBB found {len(threads)} raw items for '{keyword}'")

                for item in threads[:50]:
                    link = item.find("a", href=re.compile(r"Thread-"))
                    if not link:
                        continue

                    title = link.get_text(strip=True)
                    if not title:
                        continue

                    href = link.get("href", "")
                    if not href:
                        continue
                    if href.startswith("http"):
                        thread_url = href
                    else:
                        thread_url = f"{domain}/{href.lstrip('/')}"

                    if thread_url in seen_urls:
                        continue
                    seen_urls.add(thread_url)

                    author_el = item.find("a", href=re.compile(r"User-")) or item.find("span", class_=re.compile(r"author|username"))
                    author = author_el.get_text(strip=True) if author_el else ""
                    if not author:
                        strong = item.find("strong")
                        author = strong.get_text(strip=True) if strong else ""

                    cells = item.find_all("td")
                    posted_date = ""
                    if len(cells) >= 6:
                        raw = cells[5].get_text(strip=True)
                        raw = re.sub(r'\s*Last Post:.*', '', raw).strip()
                        if raw:
                            posted_date = _parse_mybb_date(raw)

                    results.append({
                        "title": title[:500],
                        "source_url": thread_url[:2000],
                        "snippet": "",
                        "author": author,
                        "feed_posted_at": posted_date,
                        "keyword_matched": keyword,
                        "forum_id": forum_id or "mybb_forum",
                        "forum_name": forum_name or "MyBB Forum",
                        "category": "Forum",
                        "severity": _mybb_determine_severity(title, ""),
                        "source": "forum_intelligence",
                        "discovered_at": datetime.utcnow().isoformat(),
                    })

            except httpx.TimeoutException:
                print(f"  MyBB search timeout for '{keyword}'")
            except Exception as e:
                print(f"  MyBB search error for '{keyword}': {e}")

    print(f"MyBB forum search complete: {len(results)} results")
    return results
