from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import structlog

from app.core.config import settings
from app.core.database import init_db
from app.core.redis import close_redis, get_redis
from app.core.websocket import manager, redis_subscriber

from app.api import auth, threat_intel, dark_web, news, geoint, profiles, socmint, cyber_surface, alerts, dashboard, users, admin_users

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("SENTINEL starting", version=settings.APP_VERSION)

    # Start Redis pubsub listener in background
    task = asyncio.create_task(redis_subscriber(settings.REDIS_URL))

    yield

    task.cancel()
    await close_redis()
    logger.info("SENTINEL shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Mount all routers
for router in [
    auth.router,
    users.router,
    admin_users.router,
    threat_intel.router,
    dark_web.router,
    news.router,
    geoint.router,
    profiles.router,
    socmint.router,
    cyber_surface.router,
    alerts.router,
    dashboard.router,
]:
    app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    try:
        r = await get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "redis": "ok" if redis_ok else "error",
    }


@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str, token: str = None):
    # Validate token for authenticated WS connections
    if token:
        from app.core.security import decode_token
        try:
            decode_token(token)
        except Exception:
            await websocket.close(code=1008)
            return

    await manager.connect(websocket, channel)
    await manager.connect(websocket, "all")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
        manager.disconnect(websocket, "all")
