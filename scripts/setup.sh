#!/bin/bash
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[SENTINEL]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

cd "$(dirname "$0")/.."

log "SENTINEL — Initial Setup"
echo ""

# Check Docker
docker --version >/dev/null 2>&1 || err "Docker is not installed"
docker compose version >/dev/null 2>&1 || err "Docker Compose is not installed"

# Generate .env from example
if [ ! -f .env ]; then
  cp .env.example .env
  # Generate random secret key
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  PGPASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
  sed -i "s/change_me_to_64_random_bytes_hex/$SECRET/" .env
  sed -i "s/change_me_strong_password/$PGPASS/" .env
  log ".env created with random keys"
  warn "Edit .env to add your API keys (all optional)"
else
  warn ".env already exists — skipping"
fi

# Build images
log "Building Docker images..."
docker compose build --parallel

# Start services
log "Starting services..."
docker compose up -d postgres redis

log "Waiting for PostgreSQL to be ready..."
until docker compose exec postgres pg_isready -U sentinel -q; do
  sleep 2
done

log "Running database migrations..."
docker compose run --rm backend alembic upgrade head

# Create default admin user
log "Creating default admin user..."
docker compose run --rm backend python3 -c "
import asyncio
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User

async def create_admin():
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        existing = (await db.execute(select(User).where(User.username == 'admin'))).scalar_one_or_none()
        if not existing:
            user = User(
                username='admin',
                email='admin@sentinel.local',
                hashed_password=hash_password('Sentinel@2024!'),
                role='admin',
                full_name='System Administrator',
            )
            db.add(user)
            await db.commit()
            print('Admin user created: admin / Sentinel@2024!')
        else:
            print('Admin user already exists')

asyncio.run(create_admin())
"

# Start all services
log "Starting all services..."
docker compose up -d

log ""
log "╔══════════════════════════════════════════════╗"
log "║  SENTINEL is running!                        ║"
log "║                                              ║"
log "║  URL:      http://localhost                  ║"
log "║  Username: admin                             ║"
log "║  Password: Sentinel@2024!                   ║"
log "║                                              ║"
log "║  ⚠ CHANGE THE PASSWORD IMMEDIATELY          ║"
log "╚══════════════════════════════════════════════╝"
