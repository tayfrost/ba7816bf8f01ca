import httpx
import os
import psycopg
import pytest


DB_DSN = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/sentinelai")


def _register(client: httpx.Client, email: str, company_name: str, display_name: str = "Test User") -> dict:
    resp = client.post("/auth/register", json={
        "email": email,
        "password": "securepassword123",
        "display_name": display_name,
        "company_name": company_name,
        "plan_id": 1,
    })
    return resp.json()


def test_register_returns_token(client: httpx.Client):
    resp = client.post("/auth/register", json={
        "email": "register1@example.com",
        "password": "securepassword123",
        "display_name": "Test User",
        "company_name": "Register Corp 1",
        "plan_id": 1,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_works(client: httpx.Client):
    _register(client, "login1@example.com", "Login Corp 1")

    resp = client.post("/auth/login", json={
        "email": "login1@example.com",
        "password": "securepassword123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_fails_with_wrong_password(client: httpx.Client):
    _register(client, "wrongpass@example.com", "Wrong Pass Corp")

    resp = client.post("/auth/login", json={
        "email": "wrongpass@example.com",
        "password": "notthepassword",
    })
    assert resp.status_code == 401


def test_me_endpoint_returns_user(client: httpx.Client):
    data = _register(client, "me1@example.com", "Me Corp 1")
    token = data["access_token"]

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me1@example.com"
    assert body["role"] == "biller"
    assert "user_id" in body


def test_me_fails_without_token(client: httpx.Client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_duplicate_email_rejected(client: httpx.Client):
    _register(client, "dup@example.com", "Dup Corp 1")
    resp = client.post("/auth/register", json={
        "email": "dup@example.com",
        "password": "anotherpassword",
        "company_name": "Dup Corp 2",
        "plan_id": 1,
    })
    assert resp.status_code == 409

    with psycopg.connect(DB_DSN, autocommit=True) as conn:
        dup_company_count = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE name = %s",
            ("Dup Corp 2",),
        ).fetchone()[0]
        dup_auth_count = conn.execute(
            "SELECT COUNT(*) FROM auth_users WHERE email = %s",
            ("dup@example.com",),
        ).fetchone()[0]

    assert dup_company_count == 0
    assert dup_auth_count == 1
