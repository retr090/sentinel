from celery import Celery
from app.core.config import settings
import structlog

logger = structlog.get_logger()

celery_app = Celery(
    "sentinel",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.threat_intel",
        "app.tasks.darkweb_tasks",
        "app.tasks.news",
        "app.tasks.geoint",
        "app.tasks.socmint",
        "app.tasks.cyber_surface",
        "app.tasks.alerts",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Colombo",
    enable_utc=False,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_max_retries=3,
    task_default_retry_delay=60,
    result_expires=3600,
    redbeat_redis_url=settings.REDIS_URL,
    REDBEAT_REDIS_URL=settings.REDIS_URL,
    beat_schedule={
        "fetch-threat-feeds": {
            "task": "app.tasks.threat_intel.fetch_all_feeds",
            "schedule": 3600,
            "options": {"queue": "feeds"},
        },
        "refresh-stale-iocs": {
            "task": "app.tasks.threat_intel.refresh_stale_iocs",
            "schedule": 86400,
            "options": {"queue": "feeds"},
        },
        "fetch-news": {
            "task": "app.tasks.news.fetch_all_news",
            "schedule": 1800,
            "options": {"queue": "feeds"},
        },
        "score-news-relevance": {
            "task": "app.tasks.news.score_news_relevance",
            "schedule": 3600,
            "options": {"queue": "feeds"},
        },
        "backfill-news-article-text": {
            "task": "app.tasks.news.backfill_article_text",
            "schedule": 3600,
            "options": {"queue": "feeds"},
        },
        "scan-assets": {
            "task": "app.tasks.cyber_surface.scan_all_assets",
            "schedule": 86400,
            "options": {"queue": "scans"},
        },
        "process-alerts": {
            "task": "app.tasks.alerts.process_pending_alerts",
            "schedule": 300,
            "options": {"queue": "alerts"},
        },
        "archive-old-data": {
            "task": "app.tasks.alerts.archive_old_data",
            "schedule": 86400,
            "options": {"queue": "alerts"},
        },
        "scan-ransomware-live": {
            "task": "app.tasks.darkweb_tasks.scan_ransomware_live",
            "schedule": 900.0,
            "options": {"queue": "darkweb", "expires": 840},
        },
        "scan-forums": {
            "task": "app.tasks.darkweb_tasks.scan_forums",
            "schedule": 900.0,
            "options": {"queue": "darkweb", "expires": 840},
        },
    },
)
