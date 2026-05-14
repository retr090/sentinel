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
    default_retry_delay=300,
    queue="scans",
    name="app.tasks.cyber_surface.scan_all_assets",
)
def scan_all_assets(self):
    try:
        run_async(_scan_all_assets_async())
    except Exception as exc:
        logger.error("scan_all_assets failed", exc_info=True)
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="scans",
    name="app.tasks.cyber_surface.scan_asset",
)
def scan_asset(self, asset_id: int):
    try:
        run_async(_scan_asset_async(asset_id))
    except Exception as exc:
        logger.error("scan_asset failed", asset_id=asset_id, exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _scan_all_assets_async():
    from app.core.database import AsyncSessionLocal
    from app.models.cyber_surface import MonitoredAsset
    from sqlalchemy import select
    from datetime import datetime, timezone, timedelta

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(MonitoredAsset).where(MonitoredAsset.is_active == True))
        assets = result.scalars().all()

    for asset in assets:
        scan_asset.delay(asset.id)


async def _scan_asset_async(asset_id: int):
    import httpx
    import ssl
    import socket
    from app.core.database import AsyncSessionLocal
    from app.models.cyber_surface import MonitoredAsset, AssetScan, AssetAlert
    from app.services.threat_intel import _query_shodan_internetdb
    from sqlalchemy import select
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        asset = (await db.execute(select(MonitoredAsset).where(MonitoredAsset.id == asset_id))).scalar_one_or_none()
        if not asset:
            return

        scan = AssetScan(
            asset_id=asset_id,
            scan_type="full",
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(scan)
        await db.flush()

        results = {}
        risk_score = 0.0

        # SSL check
        if asset.asset_type == "domain":
            ssl_result = await _check_ssl(asset.value)
            results["ssl"] = ssl_result
            if ssl_result.get("expires_in_days", 999) < 30:
                risk_score += 20
                alert = AssetAlert(
                    asset_id=asset_id,
                    scan_id=scan.id,
                    alert_type="ssl_expiry",
                    title=f"SSL certificate expiring in {ssl_result.get('expires_in_days')} days",
                    description=f"Asset: {asset.value}",
                    severity="HIGH" if ssl_result.get("expires_in_days", 999) < 14 else "MEDIUM",
                )
                db.add(alert)

        # Shodan passive check
        if asset.asset_type in ("domain", "ip"):
            try:
                shodan_result = await _query_shodan_internetdb(asset.value)
                results["shodan"] = shodan_result
                if shodan_result.get("vulns"):
                    risk_score += min(len(shodan_result["vulns"]) * 10, 50)
            except Exception:
                results["shodan"] = {"error": "lookup_failed"}

        scan.status = "complete"
        scan.results = results
        scan.risk_score = min(risk_score, 100)
        scan.completed_at = datetime.now(timezone.utc)

        asset.last_scanned = datetime.now(timezone.utc)
        asset.risk_score = min(risk_score, 100)
        asset.risk_grade = _score_to_grade(min(risk_score, 100))

        await db.commit()
        logger.info("Asset scan complete", asset_id=asset_id, risk_score=risk_score)


async def _check_ssl(hostname: str) -> dict:
    import ssl
    import socket
    from datetime import datetime

    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
            s.settimeout(10)
            s.connect((hostname, 443))
            cert = s.getpeercert()
            expire_str = cert.get("notAfter", "")
            if expire_str:
                expire_dt = datetime.strptime(expire_str, "%b %d %H:%M:%S %Y %Z")
                days_left = (expire_dt - datetime.utcnow()).days
                return {
                    "valid": True,
                    "expires_in_days": days_left,
                    "subject": dict(x[0] for x in cert.get("subject", [])),
                    "issuer": dict(x[0] for x in cert.get("issuer", [])),
                }
    except Exception as e:
        return {"valid": False, "error": str(e)}
    return {}


def _score_to_grade(score: float) -> str:
    if score < 20:
        return "A"
    if score < 40:
        return "B"
    if score < 60:
        return "C"
    if score < 80:
        return "D"
    return "F"
