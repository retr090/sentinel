import pytest
from unittest.mock import patch, AsyncMock
from app.api.threat_intel import detect_ioc_type
from app.services.threat_intel import calculate_risk_score


def test_detect_ioc_type_ip():
    assert detect_ioc_type("192.168.1.1") == "ip"
    assert detect_ioc_type("10.0.0.1") == "ip"
    assert detect_ioc_type("8.8.8.8") == "ip"


def test_detect_ioc_type_domain():
    assert detect_ioc_type("malware.example.com") == "domain"
    assert detect_ioc_type("evil.ru") == "domain"


def test_detect_ioc_type_hash():
    assert detect_ioc_type("d41d8cd98f00b204e9800998ecf8427e") == "hash"
    assert detect_ioc_type("aabbccddaabbccddaabbccddaabbccddaabbccddaabbccddaabbccddaabbccdd") == "hash"


def test_detect_ioc_type_url():
    assert detect_ioc_type("http://malware.com/payload.exe") == "url"
    assert detect_ioc_type("https://phishing.site/login") == "url"


def test_detect_ioc_type_email():
    assert detect_ioc_type("attacker@evil.com") == "email"


def test_calculate_risk_score_empty():
    assert calculate_risk_score({}) == 0.0


def test_calculate_risk_score_malicious():
    enrichments = {
        "greynoise": {"classification": "malicious", "noise": True},
        "alienvault": {"pulse_info": {"count": 5}},
    }
    score = calculate_risk_score(enrichments)
    assert score > 0


def test_calculate_risk_score_clean():
    enrichments = {
        "greynoise": {"classification": "benign", "noise": False},
        "alienvault": {"pulse_info": {"count": 0}},
        "shodan": {"ports": [80, 443]},
    }
    score = calculate_risk_score(enrichments)
    assert score >= 0


@pytest.mark.asyncio
async def test_ioc_search_endpoint(client, admin_token):
    response = await client.post(
        "/api/threat-intel/search?value=192.168.1.1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "ioc" in data
    assert "enrichments" in data
    assert "risk_score" in data


@pytest.mark.asyncio
async def test_list_iocs_empty(client, admin_token):
    response = await client.get(
        "/api/threat-intel/iocs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_create_ioc(client, admin_token):
    response = await client.post(
        "/api/threat-intel/iocs",
        json={"value": "10.0.0.99", "ioc_type": "ip", "analyst_notes": "Test IOC", "tags": ["test"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "10.0.0.99"
    assert data["ioc_type"] == "ip"
