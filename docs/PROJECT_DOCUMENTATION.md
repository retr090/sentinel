# SENTINEL Project Documentation

## 1. Project Overview

SENTINEL is a self-hosted OSINT and cyber operations dashboard. It combines threat intelligence, dark web monitoring, attack-surface tracking, geospatial intelligence, social monitoring, news aggregation, profile intelligence, alerting, and reporting into one web application.

The project is designed for low-resource deployments using Docker Compose and mostly free/open data sources. Optional commercial or API-key-backed sources can improve enrichment quality but are not required for the system to start.

## 2. Goals

- Provide a single dashboard for OSINT and cyber threat workflows.
- Enrich indicators of compromise such as IPs, domains, hashes, URLs, emails, CVEs, and ASNs.
- Monitor dark web, ransomware, paste, forum, and RSS sources for watchlist terms.
- Track external cyber surface assets and vulnerabilities.
- Aggregate security-relevant news and score relevance.
- Support analyst workflows with alerts, notes, reports, and user roles.
- Run on commodity VPS or free-tier cloud infrastructure.

## 3. Technology Stack

| Area | Technology |
| --- | --- |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 async, Pydantic v2 |
| Frontend | Next.js 14 App Router, React 18, TypeScript, Tailwind CSS |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 |
| Tasks | Celery, Redbeat scheduler |
| Web Server | Nginx reverse proxy |
| Auth | JWT access and refresh tokens, bcrypt password hashing, RBAC |
| Visualization | Recharts, Leaflet, React Force Graph |
| Deployment | Docker Compose |

## 4. High-Level Architecture

```text
Browser
  |
  v
Nginx :8088 / :8443
  |-- /      -> Frontend, Next.js on port 3000
  |-- /api   -> Backend, FastAPI on port 8000
  |-- /ws    -> Backend WebSocket endpoint

Backend
  |-- PostgreSQL: persistent relational data
  |-- Redis: cache, pub/sub, Celery broker, Celery result backend
  |-- Celery Worker: scans, feed fetching, enrichment jobs
  |-- Celery Beat / Redbeat: scheduled recurring tasks
```

## 5. Repository Layout

```text
sentinel/
  backend/
    app/
      api/              FastAPI route modules
      core/             config, database, Redis, security, WebSocket, Celery
      models/           SQLAlchemy models
      schemas/          Pydantic request/response schemas
      services/         OSINT integrations and business logic
      tasks/            Celery task definitions
    tests/              backend pytest suite
    alembic/            database migrations
    requirements.txt    Python dependencies
  frontend/
    app/                Next.js app routes
    components/         reusable UI/layout components
    lib/                frontend API client, store, utilities
    package.json        frontend dependencies and scripts
  docs/                 project documentation and presentation material
  nginx/                Nginx configuration and SSL mount point
  docker-compose.yml    production-style Compose stack
  docker-compose.dev.yml development overrides
  .env.example          example environment configuration
```

## 6. Core Services

| Service | Purpose | Default Exposure |
| --- | --- | --- |
| `postgres` | Stores application data | internal, `5432` in dev override |
| `redis` | Queue broker, cache, pub/sub | internal, `6379` in dev override |
| `backend` | FastAPI application | internal, `8000` in dev override |
| `celery_worker` | Executes background jobs | internal |
| `celery_beat` | Schedules recurring jobs | internal |
| `frontend` | Next.js UI | internal, `3000` in dev override |
| `nginx` | Public reverse proxy | `8088`, `8443` |

## 7. Environment Configuration

Copy `.env.example` to `.env` before starting the stack.

Required values:

| Variable | Purpose |
| --- | --- |
| `POSTGRES_PASSWORD` | PostgreSQL password used by Compose services |
| `SECRET_KEY` | JWT signing secret; use a long random value |
| `ALLOWED_ORIGINS` | Comma-separated frontend origins allowed by CORS |

Optional enrichment keys:

| Variable | Source / Feature |
| --- | --- |
| `ALIENVAULT_OTX_KEY` | AlienVault OTX enrichment |
| `GREYNOISE_API_KEY` | GreyNoise enrichment |
| `SHODAN_API_KEY` | Shodan and InternetDB enrichment |
| `IPINFO_TOKEN` | IP geolocation and ASN context |
| `HUNTER_IO_KEY` | Email intelligence |
| `NEWSAPI_KEY` | News ingestion |
| `VIRUSTOTAL_API_KEY` | VirusTotal enrichment |
| `ABUSEIPDB_API_KEY` | AbuseIPDB enrichment |
| `GROQ_API_KEY` | AI analysis for dark web / threat workflows |
| `HAVEIBEENPWNED_KEY` | Breach lookup |
| `SECURITYTRAILS_KEY` | DNS and asset discovery workflows |
| `CENSYS_API_ID`, `CENSYS_API_SECRET` | Censys enrichment |
| `INTELX_API_KEY` | IntelX-style data source integration |
| `YOUTUBE_API_KEY` | Media monitoring workflows |

Notification values:

| Variable | Purpose |
| --- | --- |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Email notifications |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | Telegram integration |

Security note: never commit `.env`. If a real key is printed in logs or terminal output, rotate it.

## 8. Local Development

Start the development stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Useful commands:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f celery_worker
docker compose exec backend python -m pytest tests/ -v
docker compose exec backend alembic upgrade head
```

Frontend checks can be run in a Node container if Node is not installed on the host:

```bash
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine npm install --legacy-peer-deps
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine npm run type-check
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine npm run lint
```

Access points:

| URL | Purpose |
| --- | --- |
| `http://localhost:8088` | Nginx-served application |
| `http://localhost:3000` | Next.js dev frontend when using dev override |
| `http://localhost:8000/health` | Backend health check when using dev override |
| `http://localhost:8000/api/docs` | FastAPI docs when `DEBUG=true` |

## 9. Creating an Admin User

Run after migrations are applied:

```bash
docker compose exec backend python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User

async def create_admin():
    async with AsyncSessionLocal() as db:
        user = User(
            username='admin',
            email='admin@example.com',
            hashed_password=hash_password('changeme'),
            role='admin',
            is_active=True,
            force_password_change=True,
        )
        db.add(user)
        await db.commit()

asyncio.run(create_admin())
"
```

Change the password immediately after first login.

## 10. Authentication And Authorization

SENTINEL uses JWT authentication with access and refresh tokens.

Roles:

| Role | Intended Access |
| --- | --- |
| `admin` | Full user and system administration |
| `analyst` | Create, update, scan, acknowledge, enrich, and operate workflows |
| `viewer` | Read-only access to dashboards and results |

Primary auth endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/login` | Login and receive token pair |
| `POST` | `/api/auth/refresh` | Refresh token pair |
| `POST` | `/api/auth/logout` | Client-side logout helper |
| `GET` | `/api/auth/me` | Current authenticated user |
| `POST` | `/api/auth/change-password` | Change password |
| `POST` | `/api/auth/users` | Admin creates user |
| `GET` | `/api/auth/users` | Admin lists users |

## 11. Application Modules

### 11.1 Dashboard

The dashboard aggregates high-level counts, risk data, recent activity, and unified search.

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/dashboard/summary` | Dashboard summary metrics |
| `GET` | `/api/dashboard/search` | Global search / redirect helper |

### 11.2 Threat Intelligence

Threat Intelligence handles IOC lookup, enrichment, risk scoring, feed collection, history, bulk jobs, exports, and Shodan helpers.

Supported IOC types include:

- `ip`
- `domain`
- `hash_md5`
- `hash_sha1`
- `hash_sha256`
- `url`
- `email`
- `cve`
- `asn`

Main enrichment sources include AlienVault OTX, ThreatFox, URLhaus, MalwareBazaar, VirusTotal, AbuseIPDB, GreyNoise, Shodan InternetDB, IPInfo, XposedOrNot, LeakCheck, CIRCL CVE, and DNS-derived checks.

Risk scoring returns both a numeric `risk_score` and a categorical `risk_level`:

| Score Range | Level |
| --- | --- |
| `75-100` | `critical` |
| `50-74.9` | `high` |
| `25-49.9` | `medium` |
| `0.1-24.9` | `low` |
| `0` | `clean` |

Key endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/threat-intel/lookup` | Primary IOC lookup and enrichment |
| `POST` | `/api/threat-intel/search` | Legacy/simple IOC search |
| `GET` | `/api/threat-intel/history` | Lookup history |
| `GET` | `/api/threat-intel/iocs` | IOC inventory |
| `POST` | `/api/threat-intel/iocs` | Create IOC |
| `POST` | `/api/threat-intel/iocs/bulk` | Bulk import IOCs |
| `GET` | `/api/threat-intel/iocs/{ioc_id}` | Get IOC |
| `PATCH` | `/api/threat-intel/iocs/{ioc_id}` | Update IOC |
| `DELETE` | `/api/threat-intel/ioc/{ioc_id}` | Archive IOC |
| `PATCH` | `/api/threat-intel/ioc/{ioc_id}/notes` | Update IOC notes |
| `POST` | `/api/threat-intel/bulk` | Start bulk lookup job |
| `GET` | `/api/threat-intel/bulk/{job_id}` | Get bulk lookup job |
| `GET` | `/api/threat-intel/export/{ioc_id}` | Export single IOC |
| `POST` | `/api/threat-intel/export/bulk` | Export multiple IOCs |
| `GET` | `/api/threat-intel/feeds` | List threat feeds |
| `GET` | `/api/threat-intel/feed-items` | List threat feed items |
| `POST` | `/api/threat-intel/feeds/refresh` | Refresh threat feeds |
| `GET` | `/api/threat-intel/shodan/search` | Shodan search helper |
| `GET` | `/api/threat-intel/shodan/count` | Shodan count helper |
| `GET` | `/api/threat-intel/shodan/domain/{domain}` | Shodan domain helper |
| `GET` | `/api/threat-intel/shodan/host/{ip}` | Shodan host helper |
| `GET` | `/api/threat-intel/shodan/status` | Shodan API status |
| `GET` | `/api/threat-intel/stats` | Threat-intel metrics |

### 11.3 Dark Web Intel

The dark web module has been intentionally narrowed to two workflows:

- Ransomware Intel: ransomware.live victim tracking for Sri Lanka only.
- Forum Intel: authenticated forum monitoring and triage.

Removed/disabled workflows:

- Generic dark web keyword/watchlist scanning.
- Manual dark web search.
- Tor/onion crawling and onion target registry.
- Ahmia/DarkSearch providers.
- Paste/RSS darkweb scanners.
- Legacy `/api/dark-web` module.

Ransomware behavior:

- Scans only ransomware.live country endpoint `/victims/LK`.
- Does not use keywords, names, domains, `.lk`, city names, or global recent-feed matching.
- Stores ransomware matches with `keyword_matched = country:LK`.
- Deduplicates by `ransomware_live + threat_actor + victim_org`.
- UI supports timeframes: 24h, 7d, 30d, 90d, 1y, and all time.
- Victim details show source link, match reason, severity, sector, data exposure status, triage controls, timestamps, summary, and raw ransomware.live fields.
- Ransomware summary cards show active groups, derived sectors, and monthly timeline counts for the selected timeframe.
- Displayed timestamps are converted to `Asia/Colombo` / GMT+05:30.

Key `/api/darkweb` endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/darkweb/stats` | Dark Web Intel summary stats |
| `GET` | `/api/darkweb/scans` | List scan history |
| `POST` | `/api/darkweb/scan/trigger` | Trigger `ransomware`, `historical`, or `forums` scan |
| `PATCH` | `/api/darkweb/mentions/{mention_id}` | Triage/update forum or ransomware mention |
| `GET` | `/api/darkweb/ransomware/victims` | Sri Lanka ransomware victims from `/victims/LK` |
| `GET` | `/api/darkweb/ransomware/stats` | Ransomware stats |
| `GET` | `/api/darkweb/ransomware/summary` | Ransomware group, sector, data-status, and timeline summaries |
| `PATCH` | `/api/darkweb/ransomware/victims/{victim_id}/seen` | Mark ransomware victim as seen |
| `GET` | `/api/darkweb/forum-mentions` | Forum mentions |

Forum credential endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/forum-credentials/list` | List configured forums |
| `POST` | `/api/forum-credentials/add` | Add forum credentials |
| `PUT` | `/api/forum-credentials/update-password/{forum_id}` | Update forum password |
| `POST` | `/api/forum-credentials/login-now/{forum_id}` | Attempt login |
| `DELETE` | `/api/forum-credentials/remove/{forum_id}` | Remove forum credentials |

### 11.4 Cyber Surface

Cyber Surface tracks monitored domains, IPs, and IP ranges. It records scans, risk grades, detected vulnerabilities, service changes, and asset alerts.

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/cyber-surface/assets` | List monitored assets |
| `POST` | `/api/cyber-surface/assets` | Create monitored asset |
| `DELETE` | `/api/cyber-surface/assets/{asset_id}` | Delete asset |
| `GET` | `/api/cyber-surface/assets/{asset_id}/scans` | List scans for asset |
| `POST` | `/api/cyber-surface/assets/{asset_id}/scan` | Trigger asset scan |
| `GET` | `/api/cyber-surface/vulnerabilities` | List vulnerabilities |
| `GET` | `/api/cyber-surface/stats` | Asset/risk statistics |

### 11.5 GEOINT

GEOINT stores geospatial intelligence items, areas of interest, and flight data used by the map views.

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/geoint/items` | List map items |
| `POST` | `/api/geoint/items` | Create map item |
| `GET` | `/api/geoint/aoi` | List areas of interest |
| `POST` | `/api/geoint/aoi` | Create area of interest |
| `DELETE` | `/api/geoint/aoi/{aoi_id}` | Delete area of interest |
| `GET` | `/api/geoint/flights` | Fetch/list flight data |
| `GET` | `/api/geoint/stats` | GEOINT statistics |

### 11.6 SOCMINT

SOCMINT monitors social keywords, stores posts, and computes sentiment-oriented statistics.

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/socmint/keywords` | List monitored social keywords |
| `POST` | `/api/socmint/keywords` | Add social keyword |
| `DELETE` | `/api/socmint/keywords/{kw_id}` | Delete social keyword |
| `GET` | `/api/socmint/posts` | List collected posts |
| `POST` | `/api/socmint/scan-now` | Trigger social scan |
| `GET` | `/api/socmint/stats` | SOCMINT statistics |

### 11.7 News And Media

News aggregates RSS/API sources, matches configured keywords, computes sentiment, and now includes relevance scoring fields.

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/news/articles` | List news articles |
| `GET` | `/api/news/sources` | List news sources |
| `POST` | `/api/news/sources` | Create news source |
| `GET` | `/api/news/keywords` | List news keywords |
| `POST` | `/api/news/keywords` | Create news keyword |
| `GET` | `/api/news/timeline` | Article timeline data |
| `POST` | `/api/news/fetch-now` | Trigger news fetch |
| `POST` | `/api/news/score-now` | Trigger relevance scoring |
| `GET` | `/api/news/alerts` | List news alerts |
| `POST` | `/api/news/alerts/{alert_id}/acknowledge` | Acknowledge news alert |
| `GET` | `/api/news/trending-keywords` | Trending keyword data |
| `GET` | `/api/news/stats` | News statistics |

### 11.8 Profile Intelligence

Profile Intelligence stores person or organization profiles, notes, enrichment data, and link-analysis-oriented metadata.

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/profiles` | List profiles |
| `POST` | `/api/profiles` | Create profile |
| `GET` | `/api/profiles/{profile_id}` | Get profile |
| `POST` | `/api/profiles/{profile_id}/notes` | Add profile note |
| `POST` | `/api/profiles/{profile_id}/enrich` | Trigger profile enrichment |
| `GET` | `/api/profiles/stats/summary` | Profile statistics |

### 11.9 Alerts And Reports

The alerts module unifies events from other modules, tracks status and assignments, and manages report generation and notification configs.

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/alerts` | List alerts |
| `POST` | `/api/alerts/{alert_id}/acknowledge` | Acknowledge alert |
| `POST` | `/api/alerts/{alert_id}/resolve` | Resolve alert |
| `POST` | `/api/alerts/{alert_id}/assign` | Assign alert |
| `GET` | `/api/alerts/reports` | List reports |
| `POST` | `/api/alerts/reports` | Create report |
| `GET` | `/api/alerts/notifications` | List notification configs |
| `POST` | `/api/alerts/notifications` | Create notification config |
| `GET` | `/api/alerts/stats` | Alert statistics |

### 11.10 User Management

Current-user endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/users/me` | Get current user profile |
| `PUT` | `/api/users/me` | Update current user profile |
| `PUT` | `/api/users/me/password` | Change current user password |

Admin user endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/admin/users` | List users |
| `POST` | `/api/admin/users` | Create user |
| `GET` | `/api/admin/users/{user_id}` | Get user |
| `PUT` | `/api/admin/users/{user_id}` | Update user |
| `PUT` | `/api/admin/users/{user_id}/reset-password` | Reset password |
| `PATCH` | `/api/admin/users/{user_id}/status` | Enable/disable user |
| `DELETE` | `/api/admin/users/{user_id}` | Delete user |

## 12. Database Model Summary

Major tables include:

| Domain | Tables |
| --- | --- |
| Auth | `users`, `audit_logs` |
| Threat Intel | `iocs`, `ioc_bulk_jobs`, `ioc_tags`, `threat_feeds`, `feed_items` |
| Dark Web | `watchlist_keywords`, `dark_web_mentions`, `breach_results`, `paste_hits` |
| Cyber Surface | `monitored_assets`, `asset_scans`, `asset_vulnerabilities`, `asset_alerts` |
| News | `news_sources`, `news_articles`, `news_keywords`, `news_alerts` |
| Alerts | `alerts`, `alert_assignments`, `reports`, `report_templates`, `notification_configs` |

Additional modules define their own GEOINT, SOCMINT, and profile models.

## 13. Background Jobs

Recurring Celery Beat schedule:

| Job | Task | Interval |
| --- | --- | --- |
| Fetch threat feeds | `app.tasks.threat_intel.fetch_all_feeds` | 1 hour |
| Refresh stale IOCs | `app.tasks.threat_intel.refresh_stale_iocs` | 24 hours |
| Fetch news | `app.tasks.news.fetch_all_news` | 30 minutes |
| Score news relevance | `app.tasks.news.score_news_relevance` | 1 hour |
| Scan assets | `app.tasks.cyber_surface.scan_all_assets` | 24 hours |
| Process alerts | `app.tasks.alerts.process_pending_alerts` | 5 minutes |
| Archive old data | `app.tasks.alerts.archive_old_data` | 24 hours |
| Scan ransomware.live | `app.tasks.darkweb_tasks.scan_ransomware_live` | 15 minutes |
| Scan forums | `app.tasks.darkweb_tasks.scan_forums` | 30 minutes |

Celery is configured with timezone `Asia/Colombo`; ransomware scan intervals remain every 15 minutes regardless of timezone.

## 14. WebSocket / Real-Time Flow

The backend exposes WebSocket connections at:

```text
/ws/{channel}?token=<jwt>
```

If a token is provided, it is validated before the socket is accepted. The connection subscribes to the requested channel and also to the `all` channel. Redis pub/sub is used to fan out messages to connected clients.

## 15. Frontend Pages

Primary routes:

| Route | Purpose |
| --- | --- |
| `/login` | Login screen |
| `/dashboard` | Main operational dashboard |
| `/threat-intel` | Threat-intel overview and workflow |
| `/threat-intel/lookup` | IOC lookup page |
| `/threat-intel/bulk` | Bulk IOC lookup/import |
| `/threat-intel/history` | IOC history |
| `/dark-web` | Dark Web Intel with Ransomware Intel and Forum Intel tabs |
| `/dark-web/forums` | Forum Intel workspace and credential management |
| `/cyber-surface` | Asset and vulnerability surface |
| `/geoint` | Map and GEOINT view |
| `/socmint` | Social monitoring |
| `/news` | News aggregation |
| `/profiles` | Profile intelligence |
| `/alerts` | Alerts and reports |
| `/admin/users` | Admin user management |
| `/settings/profile` | User profile settings |
| `/settings/password` | Password settings |

## 16. Testing And Quality Checks

Backend tests:

```bash
docker compose exec backend python -m pytest tests/ -v
```

Frontend type-check:

```bash
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine npm run type-check
```

Frontend lint:

```bash
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine npm run lint
```

Current known frontend lint warnings:

- Some React hook dependency warnings.
- Some `<img>` usage warnings where Next recommends `<Image />`.

## 17. Deployment Notes

Production-style startup:

```bash
docker compose up -d --build
```

Operational checks:

```bash
docker compose ps
docker compose logs -f nginx
docker compose logs -f backend
docker compose logs -f celery_worker
docker compose exec backend alembic current
```

Database migrations are run by the backend startup command:

```text
alembic upgrade head
```

## 18. Security Considerations

- Rotate any API key or secret that has appeared in terminal output, logs, screenshots, or commits.
- Use a strong `SECRET_KEY` and `POSTGRES_PASSWORD`.
- Keep `.env` out of Git.
- Restrict `ALLOWED_ORIGINS` to trusted domains.
- Put HTTPS in front of production deployments.
- Use least-privilege roles for users.
- Review dark web/forum credential storage and encryption before production use.
- Avoid storing unnecessary sensitive raw data from enrichments.
- Review audit logging for administrative actions.

## 19. Current Development Status

Verified during the latest development pass:

- Backend pytest suite passes.
- Frontend TypeScript type-check passes.
- Frontend lint passes with warnings only.
- Development frontend Docker image builds.
- Backend health endpoint returns healthy in the running container.

Recent development-enablement changes:

- Backend threat-intel tests aligned with current risk-score and hash-subtype behavior.
- Dev frontend Dockerfile updated for lockfile and peer dependency handling.
- ESLint configuration added for non-interactive linting.
- ESLint pinned to the Next 14-compatible v8 line.
- Generated TypeScript build info ignored.

## 20. Known Risks And Technical Debt

- Host machine may not have Python or Node installed; Docker-based workflows are the reliable path.
- The codebase contains both `/dark-web` and `/darkweb` API groups, which should eventually be consolidated or clearly versioned.
- Frontend lint still reports warnings around hook dependencies and image optimization.
- Dependency audit reports vulnerabilities in frontend packages; remediation should be tested carefully because force upgrades may break Next/React compatibility.
- `.env` in the local workspace contains real-looking keys and should be rotated if any are live.
- Some modules may be scaffolds or partially implemented and need end-to-end verification with real data.

## 21. Suggested Roadmap

### Phase 1: Stabilization

- Rotate secrets and clean environment handling.
- Add or update `.env.example` for every setting used by code.
- Consolidate duplicate dark web API naming.
- Fix frontend lint warnings.
- Add health checks for Celery queues and scheduled jobs.

### Phase 2: Module Completion

- Finish News relevance scoring UI and API behavior.
- Validate threat-intel enrichment fallbacks without API keys.
- Complete Cyber Surface scan result normalization.
- Complete GEOINT data ingestion and map marker behavior.
- Complete SOCMINT source ingestion and sentiment reporting.
- Complete profile enrichment and link analysis.

### Phase 3: Analyst Workflow

- Add unified alert creation from every module.
- Add alert assignment workflow in UI.
- Add report generation templates and export controls.
- Add audit-log screens for admin users.

### Phase 4: Production Hardening

- Add backups and restore documentation.
- Add rate limiting and request logging.
- Add structured operational dashboards.
- Add CI checks for backend tests, frontend type-check, lint, and Docker build.
- Review dependency vulnerabilities and pin safe versions.

## 22. Maintenance Commands

Backup PostgreSQL:

```bash
docker compose exec postgres pg_dump -U sentinel sentinel > sentinel_backup.sql
```

Restore PostgreSQL:

```bash
docker compose exec -T postgres psql -U sentinel sentinel < sentinel_backup.sql
```

Restart workers:

```bash
docker compose restart celery_worker celery_beat
```

Rebuild one service:

```bash
docker compose build backend
docker compose up -d backend
```

View task logs:

```bash
docker compose logs -f celery_worker
docker compose logs -f celery_beat
```

## 23. Definition Of Done For Future Features

A feature should be considered complete only when:

- Backend schema/model changes have migrations.
- API endpoints have request/response schemas.
- Analyst/admin permissions are enforced where needed.
- Frontend page handles loading, empty, error, and success states.
- Background jobs are idempotent and log useful errors.
- Tests or documented verification steps exist.
- Docker-based development commands pass.
- Sensitive values are not logged or committed.
