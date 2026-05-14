# SENTINEL

An all-in-one OSINT (Open Source Intelligence) dashboard for cyber operations. Built for self-hosted deployment on low-resource infrastructure using entirely free and open data sources.

![Stack](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi) ![Stack](https://img.shields.io/badge/Next.js-14-black?style=flat&logo=next.js) ![Stack](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat&logo=postgresql) ![Stack](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis) ![Stack](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)

---

## Modules

| Module | Description | Sources |
|--------|-------------|---------|
| **Threat Intelligence** | IOC enrichment, feed aggregation, risk scoring | AlienVault OTX, ThreatFox, URLhaus, Shodan InternetDB, GreyNoise |
| **Dark Web Monitor** | Keyword watchlist, breach lookup, paste monitoring | Ahmia, HaveIBeenPwned, paste sites |
| **Cyber Surface** | Asset discovery, port/vuln scanning, CVE tracking | Shodan InternetDB, crt.sh, WHOIS, dnspython |
| **GEOINT** | Geo-tagged threat mapping, aircraft/vessel tracking | OpenSky Network, Leaflet.js |
| **SOCMINT** | Social media keyword monitoring, sentiment analysis | Reddit public API, VADER sentiment |
| **News & Media** | RSS feed aggregation, keyword alerting | feedparser, configurable sources |
| **Profile Intelligence** | Person/org profile building, link analysis | OSINT aggregation |
| **Alerts & Reports** | Unified alert management, PDF report generation | WeasyPrint, Jinja2 |

---

## Tech Stack

- **Backend:** Python 3.11, FastAPI (async), SQLAlchemy 2.0, Alembic, Celery + Redbeat
- **Frontend:** Next.js 14 App Router, TypeScript, Tailwind CSS, Recharts, Leaflet.js, Zustand
- **Infrastructure:** PostgreSQL 16, Redis 7, Nginx, Docker Compose
- **Auth:** JWT (access + refresh tokens), bcrypt, role-based access (admin / analyst / viewer)
- **Real-time:** WebSocket via Redis pub/sub

---

## Requirements

- Docker and Docker Compose
- 2GB+ RAM (tested on Oracle Cloud Free Tier — 1 OCPU, 6GB RAM)
- Ports 8088 (HTTP) and 8443 (HTTPS) available

---

## Quick Start

**1. Clone and configure**

```bash
git clone https://github.com/retr090/sentinel.git
cd sentinel
cp .env.example .env   # edit values before proceeding
```

**2. Configure `.env`**

```env
SECRET_KEY=your-secret-key-min-32-chars
POSTGRES_PASSWORD=your-db-password
ALLOWED_ORIGINS=http://localhost:8088

# Optional API keys (enrich data quality)
OTX_API_KEY=
SHODAN_API_KEY=
GREYNOISE_API_KEY=
HIBP_API_KEY=
```

**3. Start services**

```bash
docker compose up -d
```

**4. Create admin user**

```bash
docker compose exec backend python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User

async def create_admin():
    async with AsyncSessionLocal() as db:
        user = User(username='admin', email='admin@example.com',
                    hashed_password=hash_password('changeme'),
                    role='admin', is_active=True)
        db.add(user)
        await db.commit()

asyncio.run(create_admin())
"
```

Access the dashboard at **http://localhost:8088**

---

## Development

```bash
# Run backend tests
docker compose exec backend python -m pytest tests/ -v

# View logs
docker compose logs -f backend
docker compose logs -f celery_worker
```

---

## Architecture

```
nginx (8088/8443)
├── /         → frontend (Next.js, port 3000)
└── /api      → backend (FastAPI, port 8000)
               ├── PostgreSQL (34-table schema)
               ├── Redis (cache + pub/sub + task queue)
               ├── Celery Worker (feed/scan tasks)
               └── Celery Beat (scheduled jobs)
```

---

## License

MIT
