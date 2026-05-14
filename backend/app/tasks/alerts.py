from celery import shared_task
from celery.utils.log import get_task_logger
import asyncio

logger = get_task_logger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="alerts",
    name="app.tasks.alerts.process_pending_alerts",
)
def process_pending_alerts(self):
    try:
        run_async(_process_alerts_async())
    except Exception as exc:
        logger.error("process_pending_alerts failed", exc_info=True)
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="alerts",
    name="app.tasks.alerts.archive_old_data",
)
def archive_old_data(self):
    try:
        run_async(_archive_old_data_async())
    except Exception as exc:
        logger.error("archive_old_data failed", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="alerts",
    name="app.tasks.alerts.generate_report",
)
def generate_report(self, report_id: int):
    try:
        run_async(_generate_report_async(report_id))
    except Exception as exc:
        logger.error("generate_report failed", report_id=report_id, exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _process_alerts_async():
    from app.core.database import AsyncSessionLocal
    from app.models.alerts import Alert, NotificationConfig
    from app.core.redis import publish_event
    from sqlalchemy import select
    from datetime import datetime, timezone, timedelta

    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(NotificationConfig).where(NotificationConfig.is_active == True))
        configs = result.scalars().all()

        for config in configs:
            min_sev = config.min_severity
            min_order = severity_order.get(min_sev, 99)

            alerts_q = select(Alert).where(
                Alert.status == "open",
                Alert.is_archived == False,
            )
            if config.modules:
                alerts_q = alerts_q.where(Alert.module.in_(config.modules))

            alerts_result = await db.execute(alerts_q.order_by(Alert.triggered_at.desc()).limit(10))
            alerts = alerts_result.scalars().all()

            for alert in alerts:
                if severity_order.get(alert.severity, 99) <= min_order:
                    await _send_notification(config, alert)


async def _send_notification(config, alert):
    channel = config.channel_type
    cfg = config.config or {}

    if channel == "telegram" and cfg.get("bot_token") and cfg.get("chat_id"):
        await _send_telegram(cfg["bot_token"], cfg["chat_id"], alert)
    elif channel == "webhook" and cfg.get("url"):
        await _send_webhook(cfg["url"], alert)


async def _send_telegram(bot_token: str, chat_id: str, alert) -> None:
    import httpx
    message = f"🚨 *{alert.severity}* — {alert.title}\nModule: {alert.module}\n{alert.description or ''}"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            )
    except Exception as e:
        logger.warning("Telegram notification failed", error=str(e))


async def _send_webhook(url: str, alert) -> None:
    import httpx
    payload = {
        "title": alert.title,
        "severity": alert.severity,
        "module": alert.module,
        "description": alert.description,
        "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            await client.post(url, json=payload)
    except Exception as e:
        logger.warning("Webhook notification failed", url=url, error=str(e))


async def _archive_old_data_async():
    from app.core.database import AsyncSessionLocal
    from app.core.config import settings
    from app.models.threat_intel import IOC, FeedItem
    from app.models.dark_web import DarkWebMention
    from app.models.news import NewsArticle
    from app.models.alerts import Alert
    from sqlalchemy import update
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.DATA_RETENTION_DAYS)

    async with AsyncSessionLocal() as db:
        for model in (FeedItem, DarkWebMention, NewsArticle):
            await db.execute(
                update(model).where(model.created_at < cutoff, model.is_archived == False).values(is_archived=True)
            )

        await db.execute(
            update(Alert).where(Alert.triggered_at < cutoff, Alert.status.in_(["resolved", "false_positive"]), Alert.is_archived == False).values(is_archived=True)
        )

        await db.commit()
        logger.info("Old data archived", cutoff=cutoff.isoformat())


async def _generate_report_async(report_id: int):
    from app.core.database import AsyncSessionLocal
    from app.models.alerts import Report
    from sqlalchemy import select
    from datetime import datetime, timezone
    import os

    async with AsyncSessionLocal() as db:
        report = (await db.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
        if not report:
            return

        report.status = "generating"
        await db.flush()

        try:
            html = await _build_report_html(db, report)
            from app.core.config import settings
            os.makedirs(settings.REPORTS_DIR, exist_ok=True)
            file_path = os.path.join(settings.REPORTS_DIR, f"report_{report_id}.pdf")

            import weasyprint
            weasyprint.HTML(string=html).write_pdf(file_path)

            report.file_path = file_path
            report.status = "ready"
            report.generated_at = datetime.now(timezone.utc)
        except Exception as e:
            report.status = "failed"
            report.error_message = str(e)
            logger.error("Report generation failed", report_id=report_id, error=str(e))

        await db.commit()


async def _build_report_html(db, report) -> str:
    from datetime import datetime

    sections = []
    date_from = report.date_from or (datetime.utcnow().replace(hour=0, minute=0, second=0))
    date_to = report.date_to or datetime.utcnow()

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{ font-family: Arial, sans-serif; color: #333; margin: 40px; }}
h1 {{ color: #1a1a2e; border-bottom: 2px solid #00ff88; padding-bottom: 10px; }}
h2 {{ color: #16213e; margin-top: 30px; }}
.header {{ background: #0a0d0f; color: #00ff88; padding: 20px; text-align: center; }}
.section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
.badge {{ display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 12px; font-weight: bold; }}
.critical {{ background: #ef4444; color: white; }}
.high {{ background: #f59e0b; color: white; }}
.medium {{ background: #3b82f6; color: white; }}
.low {{ background: #10b981; color: white; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f3f4f6; }}
</style>
</head>
<body>
<div class="header">
<h1>SENTINEL — Intelligence Report</h1>
<p>Classification: RESTRICTED | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</div>
<div class="section">
<h2>{report.title}</h2>
<p><strong>Type:</strong> {report.report_type.upper()}</p>
<p><strong>Period:</strong> {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}</p>
</div>
<div class="section">
<h2>Executive Summary</h2>
<p>This report summarises intelligence collected during the specified period across all monitored modules.</p>
</div>
</body>
</html>"""
    return html
