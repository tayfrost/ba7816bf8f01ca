import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_returns_token(client: AsyncClient):
    response = await client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword123",
        "name": "Test",
        "surname": "User",
        "company_name": "Test Corp",
        "plan_id": 1,
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_works(client: AsyncClient):
    # Register first
    await client.post("/auth/register", json={
        "email": "login@example.com",
        "password": "securepassword123",
        "name": "Login",
        "surname": "User",
        "company_name": "Login Corp",
        "plan_id": 1,
    })

    # Login
    response = await client.post("/auth/login", json={
        "email": "login@example.com",
        "password": "securepassword123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_fails_with_wrong_password(client: AsyncClient):
    # Register first
    await client.post("/auth/register", json={
        "email": "wrong@example.com",
        "password": "correctpassword",
        "name": "Wrong",
        "surname": "Pass",
        "company_name": "Wrong Corp",
        "plan_id": 1,
    })

    # Login with wrong password
    response = await client.post("/auth/login", json={
        "email": "wrong@example.com",
        "password": "incorrectpassword",
    })
    assert response.status_code == 401
