import httpx
import pytest


def _register(client: httpx.Client, email: str, company_name: str) -> str:
    resp = client.post("/auth/register", json={
        "email": email,
        "password": "testpassword123",
        "company_name": company_name,
        "plan_id": 1,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_get_company_info(client: httpx.Client):
    token = _register(client, "compget@test.com", "Get Company Corp")
    resp = client.get("/companies/me", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Get Company Corp"


def test_update_company_name(client: httpx.Client):
    token = _register(client, "compupdate@test.com", "Old Name Corp")
    resp = client.patch("/companies/me", json={"name": "New Name Corp"}, headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name Corp"


def test_soft_delete_company(client: httpx.Client):
    token = _register(client, "compdel@test.com", "Delete Corp")
    resp = client.delete("/companies/me", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Company deleted"


def test_login_fails_after_soft_delete(client: httpx.Client):
    token = _register(client, "compgone@test.com", "Gone Corp")
    client.delete("/companies/me", headers=_auth(token))

    resp = client.post("/auth/login", json={
        "email": "compgone@test.com",
        "password": "testpassword123",
    })
    assert resp.status_code == 401


def test_get_company_fails_after_soft_delete(client: httpx.Client):
    token = _register(client, "compinvis@test.com", "Invisible Corp")
    client.delete("/companies/me", headers=_auth(token))

    resp = client.get("/companies/me", headers=_auth(token))
    assert resp.status_code == 401
