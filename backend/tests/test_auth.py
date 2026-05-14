import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_token


def test_hash_and_verify_password():
    password = "secure_password_123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_create_and_decode_access_token():
    token = create_access_token(42, {"role": "analyst"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "analyst"
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    response = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "testpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    response = await client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client, admin_token):
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_me_endpoint_unauthenticated(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_user_admin_only(client, admin_token):
    response = await client.post(
        "/api/auth/users",
        json={
            "username": "newanalyst",
            "email": "analyst@test.com",
            "password": "password123",
            "role": "analyst",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newanalyst"
    assert data["role"] == "analyst"
