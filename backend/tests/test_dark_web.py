import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_list_keywords_empty(client, admin_token):
    response = await client.get(
        "/api/dark-web/keywords",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_keyword(client, admin_token):
    response = await client.post(
        "/api/dark-web/keywords",
        json={"keyword": "test-keyword-sentinel", "category": "general", "severity": "HIGH"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["keyword"] == "test-keyword-sentinel"
    assert data["severity"] == "HIGH"


@pytest.mark.asyncio
async def test_create_duplicate_keyword(client, admin_token):
    await client.post(
        "/api/dark-web/keywords",
        json={"keyword": "duplicate-kw", "category": "general", "severity": "MEDIUM"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.post(
        "/api/dark-web/keywords",
        json={"keyword": "duplicate-kw", "category": "general", "severity": "MEDIUM"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_mentions_empty(client, admin_token):
    response = await client.get(
        "/api/dark-web/mentions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_dark_web_stats(client, admin_token):
    response = await client.get(
        "/api/dark-web/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_mentions" in data
    assert "keywords_active" in data


@pytest.mark.asyncio
async def test_breach_lookup_no_key(client, admin_token):
    with patch("app.services.dark_web.lookup_hibp", new_callable=AsyncMock) as mock_hibp:
        with patch("app.services.dark_web.lookup_paste_sites", new_callable=AsyncMock) as mock_paste:
            mock_hibp.return_value = []
            mock_paste.return_value = []
            response = await client.post(
                "/api/dark-web/breach-lookup",
                json={"query": "test@example.com", "query_type": "email"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert response.status_code == 200
