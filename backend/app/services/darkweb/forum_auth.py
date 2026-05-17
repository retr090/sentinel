import re
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, Tuple

from ..encryption import decrypt_password

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded",
}


async def login_mybb(
    base_url: str,
    username: str,
    password: str,
    login_url: str = None,
) -> Tuple[bool, Dict[str, str], str]:
    """Login to a MyBB forum. Returns (success, cookies, error)."""
    if not login_url:
        login_url = f"{base_url}/member.php"

    try:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers=BROWSER_HEADERS,
        ) as client:
            # Fetch login page to extract hidden fields (CSRF / my_post_key)
            get_r = await client.get(login_url, params={"action": "login"})
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

            initial_cookies = dict(get_r.cookies)

            login_data = {
                "action": "do_login",
                "username": username,
                "password": password,
                "remember": "yes",
                "submit": "Login",
                **hidden_fields,
            }

            post_r = await client.post(
                login_url,
                params={"action": "do_login"},
                data=login_data,
                cookies=initial_cookies,
                headers={**BROWSER_HEADERS, "Referer": f"{login_url}?action=login"},
            )

            all_cookies: Dict[str, str] = {}
            for resp in post_r.history:
                all_cookies.update(dict(resp.cookies))
            all_cookies.update(dict(post_r.cookies))

            page_text = post_r.text.lower()

            failed_indicators = [
                "incorrect username", "wrong password", "invalid username",
                "login failed", "banned", "you have been banned",
            ]
            if any(ind in page_text for ind in failed_indicators):
                return False, {}, "Login failed — incorrect username or password"

            success_indicators = [
                "logout", "usercp.php", "welcome back",
                "my account", "user control panel",
            ]
            mybb_cookies = {
                k: v for k, v in all_cookies.items()
                if any(x in k.lower() for x in ["mybb", "session", "user", "login", "sid", "auth"])
            }

            if any(ind in page_text for ind in success_indicators) or mybb_cookies:
                print(f"MyBB login successful — {len(all_cookies)} cookies")
                return True, all_cookies, ""

            # Last resort: check usercp directly
            verify_r = await client.get(f"{base_url}/usercp.php", cookies=all_cookies)
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


async def ensure_valid_session(forum, db) -> Tuple[bool, str]:
    """
    Verify session cookies are still valid.
    If expired and auto_login is enabled, re-authenticate.
    Returns (is_valid, error_message).
    """
    from .sources.breached_st import check_session_valid

    if forum.session_cookies:
        try:
            is_valid = await check_session_valid(forum.session_cookies)
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

    # Rate-limit login attempts: 5-minute cooldown
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
