import pytest
import uuid
from datetime import datetime

from app.models.darkweb import DarkWebMention
from app.services.darkweb.sources.ransomware_live import parse_victim


@pytest.mark.asyncio
async def test_leak_intel_stats(client, admin_token):
    response = await client.get(
        "/api/darkweb/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "mentions_24h" in data
    assert "ransomware_24h" in data
    assert "forum_mentions_24h" in data


@pytest.mark.asyncio
async def test_ransomware_stats_counts_unseen_victims(client, admin_token, test_db):
    before_response = await client.get(
        "/api/darkweb/ransomware/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    before = before_response.json()

    seen_victim = DarkWebMention(
        id=uuid.uuid4(),
        keyword_matched="country:LK",
        source="ransomware_live",
        title="Seen ransomware victim",
        severity="HIGH",
        victim_org="Seen Org",
        victim_country="LK",
        discovered_at=datetime.utcnow(),
        analyst_seen_at=datetime.utcnow(),
        is_reviewed=False,
        is_false_positive=False,
    )
    unseen_victim = DarkWebMention(
        id=uuid.uuid4(),
        keyword_matched="country:LK",
        source="ransomware_live",
        title="Unseen ransomware victim",
        severity="HIGH",
        victim_org="Unseen Org",
        victim_country="LK",
        discovered_at=datetime.utcnow(),
        analyst_seen_at=None,
        is_reviewed=False,
        is_false_positive=False,
    )
    test_db.add_all([seen_victim, unseen_victim])
    await test_db.commit()

    response = await client.get(
        "/api/darkweb/ransomware/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_victims"] == before["total_victims"] + 2
    assert data["unread_ransomware_count"] == before["unread_ransomware_count"] + 1
    assert "last_7_days" in data
    assert "last_30_days" in data
    assert "critical_high" in data


@pytest.mark.asyncio
async def test_mark_ransomware_victim_seen(client, admin_token, test_db):
    before_response = await client.get(
        "/api/darkweb/ransomware/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    before_unread = before_response.json()["unread_ransomware_count"]

    victim = DarkWebMention(
        id=uuid.uuid4(),
        keyword_matched="country:LK",
        source="ransomware_live",
        title="Mark seen ransomware victim",
        severity="HIGH",
        victim_org="Mark Seen Org",
        victim_country="LK",
        discovered_at=datetime.utcnow(),
        analyst_seen_at=None,
        is_reviewed=False,
        is_false_positive=False,
    )
    test_db.add(victim)
    await test_db.commit()

    added_response = await client.get(
        "/api/darkweb/ransomware/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert added_response.json()["unread_ransomware_count"] == before_unread + 1

    response = await client.patch(
        f"/api/darkweb/ransomware/victims/{victim.id}/seen",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["analyst_seen_at"] is not None

    stats_response = await client.get(
        "/api/darkweb/ransomware/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert stats_response.status_code == 200
    assert stats_response.json()["unread_ransomware_count"] == before_unread


@pytest.mark.asyncio
async def test_ransomware_victims_return_feed_posted_and_collected_dates(client, admin_token, test_db):
    feed_posted_at = datetime(2026, 5, 16)
    collected_at = datetime(2026, 5, 22, 8, 30)
    victim = DarkWebMention(
        id=uuid.uuid4(),
        keyword_matched="country:LK",
        source="ransomware_live",
        title="Posted date ransomware victim",
        severity="HIGH",
        victim_org="Posted Date Org",
        victim_country="LK",
        feed_posted_at=feed_posted_at,
        published_at=feed_posted_at,
        discovered_at=collected_at,
        analyst_seen_at=collected_at,
        is_reviewed=False,
        is_false_positive=False,
    )
    test_db.add(victim)
    await test_db.commit()

    response = await client.get(
        "/api/darkweb/ransomware/victims",
        params={"days": 30, "limit": 200},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    item = next(v for v in response.json()["victims"] if v["id"] == str(victim.id))
    assert item["feed_posted_at"] == feed_posted_at.isoformat()
    assert item["posted_at"] == feed_posted_at.isoformat()
    assert item["collected_at"] == collected_at.isoformat()
    assert item["ingested_at"] == collected_at.isoformat()
    assert item["discovered_at"] == feed_posted_at.isoformat()


@pytest.mark.asyncio
async def test_ransomware_victims_prefer_raw_attackdate_over_ingest_date(client, admin_token, test_db):
    feed_posted_at = datetime(2026, 5, 16)
    collected_at = datetime(2026, 5, 22, 8, 30)
    victim = DarkWebMention(
        id=uuid.uuid4(),
        keyword_matched="country:LK",
        source="ransomware_live",
        title="Raw posted date ransomware victim",
        severity="HIGH",
        victim_org="Raw Posted Date Org",
        victim_country="LK",
        feed_posted_at=collected_at,
        discovered_at=collected_at,
        raw_data={"attackdate": "2026-05-16T00:00:00+00:00"},
        analyst_seen_at=collected_at,
        is_reviewed=False,
        is_false_positive=False,
    )
    test_db.add(victim)
    await test_db.commit()

    response = await client.get(
        "/api/darkweb/ransomware/victims",
        params={"days": 30, "limit": 200},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    item = next(v for v in response.json()["victims"] if v["id"] == str(victim.id))
    assert item["feed_posted_at"] == feed_posted_at.isoformat()
    assert item["collected_at"] == collected_at.isoformat()


def test_ransomware_parser_uses_source_attackdate_for_feed_posted_at():
    parsed = parse_victim(
        {
            "victim": "NKAR Travels & Tours",
            "group": "payload",
            "country": "LK",
            "attackdate": "2026-05-16T00:00:00+00:00",
            "discovered": "2026-05-22T08:30:00+00:00",
        },
        is_lk=True,
        keyword_matched="country:LK",
    )

    assert parsed["feed_posted_at"] == datetime(2026, 5, 16)
