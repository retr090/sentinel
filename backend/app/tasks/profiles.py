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
    default_retry_delay=60,
    queue="feeds",
    name="app.tasks.profiles.enrich_profile",
)
def enrich_profile(self, profile_id: int):
    try:
        run_async(_enrich_profile_async(profile_id))
    except Exception as exc:
        logger.error("enrich_profile failed", profile_id=profile_id, exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _enrich_profile_async(profile_id: int):
    import httpx
    from app.core.database import AsyncSessionLocal
    from app.models.profile import Profile, ProfileAttribute
    from sqlalchemy import select
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        profile = (await db.execute(select(Profile).where(Profile.id == profile_id))).scalar_one_or_none()
        if not profile:
            return

        attrs = []
        ptype = profile.profile_type
        value = profile.query_value

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0), follow_redirects=True) as client:
            if ptype in ("domain", "ip"):
                # WHOIS
                whois_data = await _whois_lookup(value)
                if whois_data:
                    attrs.append(ProfileAttribute(profile_id=profile_id, attr_type="whois", attr_key="whois", attr_value=str(whois_data)[:2000], source="python-whois"))

                # DNS
                dns_data = await _dns_lookup(value)
                for record_type, records in dns_data.items():
                    for record in records:
                        attrs.append(ProfileAttribute(profile_id=profile_id, attr_type="dns", attr_key=record_type, attr_value=record, source="dnspython"))

                # Certificate Transparency
                if ptype == "domain":
                    crt_data = await _crtsh_lookup(client, value)
                    for cert in crt_data[:20]:
                        attrs.append(ProfileAttribute(profile_id=profile_id, attr_type="cert", attr_key="san", attr_value=cert.get("name_value", ""), source="crt.sh"))

                # IPinfo
                if ptype == "ip":
                    ipinfo_data = await _ipinfo_lookup(client, value)
                    if ipinfo_data:
                        attrs.append(ProfileAttribute(profile_id=profile_id, attr_type="geo", attr_key="ipinfo", attr_value=str(ipinfo_data)[:1000], source="ipinfo.io"))

            elif ptype == "email":
                # Extract domain and do domain lookups
                domain = value.split("@")[-1] if "@" in value else value
                dns_data = await _dns_lookup(domain)
                for record_type, records in dns_data.items():
                    for record in records:
                        attrs.append(ProfileAttribute(profile_id=profile_id, attr_type="dns", attr_key=record_type, attr_value=record, source="dnspython"))

            # Wayback Machine
            wayback = await _wayback_check(client, value)
            if wayback:
                attrs.append(ProfileAttribute(profile_id=profile_id, attr_type="history", attr_key="wayback", attr_value=str(wayback), source="archive.org"))

        for attr in attrs:
            db.add(attr)

        profile.last_updated = datetime.now(timezone.utc)
        await db.commit()
        logger.info("Profile enriched", profile_id=profile_id, attributes=len(attrs))


async def _whois_lookup(value: str) -> dict:
    try:
        import whois
        result = whois.whois(value)
        return {k: str(v) for k, v in result.items() if v and k in ("registrar", "creation_date", "expiration_date", "name_servers", "emails")}
    except Exception as e:
        logger.warning("WHOIS failed", value=value, error=str(e))
        return {}


async def _dns_lookup(domain: str) -> dict:
    import dns.resolver
    results = {}
    for record_type in ("A", "AAAA", "MX", "NS", "TXT"):
        try:
            answers = dns.resolver.resolve(domain, record_type, lifetime=5)
            results[record_type] = [str(r) for r in answers]
        except Exception:
            pass
    return results


async def _crtsh_lookup(client, domain: str) -> list:
    try:
        r = await client.get(f"https://crt.sh/?q={domain}&output=json")
        if r.status_code == 200:
            return r.json()[:30]
    except Exception:
        pass
    return []


async def _ipinfo_lookup(client, ip: str) -> dict:
    from app.core.config import settings
    url = f"https://ipinfo.io/{ip}/json"
    if settings.IPINFO_TOKEN:
        url += f"?token={settings.IPINFO_TOKEN}"
    try:
        r = await client.get(url)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


async def _wayback_check(client, value: str) -> dict:
    try:
        r = await client.get(f"https://archive.org/wayback/available?url={value}")
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}
