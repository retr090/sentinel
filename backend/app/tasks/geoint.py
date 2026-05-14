from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="feeds",
    name="app.tasks.geoint.sync_geo_items",
)
def sync_geo_items(self):
    pass
