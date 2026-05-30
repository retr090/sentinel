# Sentinel Project — Session Context

## Project
OSINT dashboard with ransomware tracking, forum intelligence, AI analysis, threat intel feeds.

## Stack
- Backend: FastAPI + SQLAlchemy async + Celery + PostgreSQL + Redis
- Frontend: Next.js (App Router) with Tailwind
- Auth: JWT-based
- Deployment: Docker Compose (nginx, backend, frontend, celery_worker, celery_beat, postgres, redis)
- Secrets: Environment file (not committed) for DB, JWT, encryption keys, Groq API key

## Forum Intel Module

### Supported Forums
- **darkforums.su** — MyBB software, credentials stored encrypted with Fernet (FORUM_ENCRYPTION_KEY)
- **breached.st / BreachForums** — XenForo software, handled by `run_full_scan` in breached_st.py

### Key Files
- `backend/app/services/darkweb/forum_auth.py` — MyBB login, session validation, search
- `backend/app/services/darkweb/sources/breached_st.py` — XenForo scanner
- `backend/app/tasks/darkweb_tasks.py` — scan orchestration, mention saving
- `backend/app/api/darkweb.py` — API endpoints (forum-mentions, scan trigger)
- `backend/app/models/darkweb.py` — DarkWebMention model
- `frontend/app/dark-web/page.tsx` — main dark web page (forum intel tab + detail modal)
- `frontend/app/dark-web/forums/page.tsx` — full forum workspace (table, filters, expandable detail)

### Authentication Flow (MyBB)
1. `ensure_valid_session` checks existing cookies via `_check_mybb_session` (GET usercp.php → 200 OK)
2. If expired, `auto_login_forum` → `login_mybb`:
   - GET member.php?action=login, extract `my_post_key` from hidden form field
   - POST member.php with username, password, my_post_key, action=do_login
   - Must get `mybbuser` cookie in the response
   - Failed indicators (page text): "incorrect username", "wrong password", etc.
3. Cookies stored in DB as dict, encrypted password stored with Fernet

### MyBB Search
- POST `/search.php` with keywords, action=do_search, postthread=1, showresults=threads
- Follows 302 redirect to results page with SID
- Parses thread rows (class `inline_row`), extracts title, author, last post date from cell 5
- `_parse_mybb_date()` handles: "X hours ago", "Yesterday", "DD-MM-YY, HH:MM AM/PM"
- Result dict keys: `title`, `source_url`, `snippet`, `author`, `feed_posted_at` (datetime), `keyword_matched`, `severity`, `source`, `discovered_at`
- `domain` extracted from `forum_url` via `urlsplit` (not using base_url directly)

### URLs & Domain Handling
- `forum_url` stored as `https://darkforums.su/index.php` — always extract domain with `urlsplit`
- `domain = f"{parsed.scheme}://{parsed.netloc}"` — used for all member.php, search.php, usercp.php calls
- Thread URLs: `{domain}/Thread-{slug}`

### API Endpoints
- `GET /darkweb/forum-mentions` — paginated with filters: `keyword`, `severity`, `days`, `year`, `sort_by` (discovered_at|feed_posted_at), `search_in` (all|title)
- `PATCH /darkweb/mentions/{id}` — update triage, notes, review status
- `POST /darkweb/scan/trigger?scan_type=forums` — trigger scan
- `GET /forums/list` — list configured forum credentials
- `POST /forums/add` — add new forum

### Data Model (darkweb_mentions)
Key date columns: `discovered_at` (when found), `feed_posted_at` (thread last post date), `published_at`
Key text columns: `source`, `source_url`, `title`, `snippet`, `severity`, `keyword_matched`, `threat_actor`
Review columns: `is_reviewed`, `is_false_positive`, `triage_status`, `analyst_notes`

### Frontend Features Added
- **Main dark-web page forum tab**: Stats cards, clickable mentions → detail modal with source URL, snippet, AI analysis, review buttons (Mark Reviewed, False Positive), metadata (Thread Date, Discovered, Threat Actor)
- **Forum workspace page**: Sort by thread date / found date dropdown, year filter (2026/2025/all), "Title only" checkbox, Thread Date column, "Open Thread on Forum" button
- Mention titles are direct links to forum threads (opens in new tab)

### Gotchas / Fixed Issues
- `Content-Type: application/x-www-form-urlencoded` in BROWSER_HEADERS breaks GET requests
- `"banned"` in failed_indicators matches benign text ("banned users can appeal") — removed
- `feed_posted_at` must be a `datetime` object, not ISO string, for PostgreSQL compatibility
- Login cooldown: 300s between retries, tracked by `last_login_attempt` and `login_attempts`
- MyBB search returns 302 redirect to SID-based results page; httpx `follow_redirects=True` handles it
- Thread URL pattern: `Thread-{slug}` not `showthread.php?tid=`

## Ransomware Module
- Fetches from `https://api.ransomware.live/v2/victims/LK` (Sri Lanka country filter)
- Data model includes: threat_actor, victim_org, victim_country, sector, data_status, feed_posted_at
- Frontend shows ransomware victims table, detail modal with triage, source URL, stats/summary widgets

## Current State
- All containers rebuilt with latest code deployed
- 23 forum mentions stored with `feed_posted_at` populated
- Forum scan works end-to-end: login → search → save → display
- AI enrichment via Groq (llama-3.3-70b-versatile) hits rate limits easily

## Git Branch
- Working on `dev` branch
- Remote: `git@github.com:retr090/sentinel.git`
- Docs/ folder excluded from git tracking
