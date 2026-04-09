"""
conftest.py — shared pytest configuration.

Ensures the repo root is on sys.path so imports like
`from app.services.x import y` resolve correctly regardless of
where pytest is invoked from.
"""

import sys
import os
import httpx
import pytest
from datetime import datetime

# Insert the repo root (parent of this file) at the front of sys.path
sys.path.insert(0, os.path.dirname(__file__))

# API base URL from environment, default to docker-compose service name for container execution
API_BASE_URL = os.getenv("INTERNAL_API_URL", "http://api:8000")


@pytest.fixture(scope="session")
def test_plan_id():
    """Resolve an existing plan_id from API instead of assuming identity starts at 1."""
    response = httpx.get(f"{API_BASE_URL}/plans", timeout=10.0)
    response.raise_for_status()
    plans = response.json()
    if not plans:
        raise RuntimeError("No subscription plans found. Seed at least one plan before running webhook tests.")

    free_plan = next((p for p in plans if str(p.get("plan_name", "")).strip().lower() == "free"), None)
    return int((free_plan or plans[0])["plan_id"])


@pytest.fixture(scope="function")
def test_company_id(test_plan_id):
    """Create a test company via API, return company_id, hard-delete after test."""
    timestamp = datetime.now(datetime.UTC).strftime("%Y%m%d%H%M%S%f")
    company_name = f"test-company-{timestamp}"

    # Create company
    response = httpx.post(
        f"{API_BASE_URL}/companies",
        json={"name": company_name, "plan_id": test_plan_id},
        timeout=10.0,
    )
    if response.status_code != 201:
        print(f"Company creation failed: {response.status_code} {response.text}")
    response.raise_for_status()
    company_id = response.json()["company_id"]

    yield company_id

    # Cleanup: hard-delete via internal API endpoint (CASCADE removes all children).
    try:
        httpx.delete(
            f"{API_BASE_URL}/internal/companies/{company_id}",
            timeout=10.0,
        )
    except Exception as e:
        print(f"Warning: cleanup failed for company_id={company_id}: {e}")
