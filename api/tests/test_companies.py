import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str, company_name: str) -> str:
    resp = await client.post("/auth/register", json={
        "email": email,
        "password": "testpassword123",
        "name": "Test User",
        "company_name": company_name,
        "plan_id": 1,
    })
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_company_via_registration(client: AsyncClient):
    token = await _register(client, "comp1@test.com", "Test Company 1")
    assert token


@pytest.mark.asyncio
async def test_get_company_info(client: AsyncClient):
    token = await _register(client, "comp2@test.com", "Test Company 2")
    response = await client.get("/companies/me", headers=_auth_headers(token))
    assert response.status_code == 200
    assert response.json()["company_name"] == "Test Company 2"


@pytest.mark.asyncio
async def test_soft_delete_company(client: AsyncClient):
    token = await _register(client, "comp3@test.com", "Delete Corp")
    response = await client.delete("/companies/me", headers=_auth_headers(token))
    assert response.status_code == 200
    assert response.json()["detail"] == "Company deleted"


@pytest.mark.asyncio
async def test_login_fails_after_soft_delete(client: AsyncClient):
    token = await _register(client, "comp4@test.com", "Gone Corp")

    # Soft delete the company
    await client.delete("/companies/me", headers=_auth_headers(token))

    # Try to login — should fail
    response = await client.post("/auth/login", json={
        "email": "comp4@test.com",
        "password": "testpassword123",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_company_fails_after_soft_delete(client: AsyncClient):
    token = await _register(client, "comp5@test.com", "Invisible Corp")

    # Soft delete
    await client.delete("/companies/me", headers=_auth_headers(token))

    # Try to get company — should fail (user is now inactive)
    response = await client.get("/companies/me", headers=_auth_headers(token))
    assert response.status_code == 401
