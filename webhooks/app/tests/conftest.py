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
    """Ensure a test plan exists. Create it if not."""
    # For now, hardcode plan_id=1. The test runner (run_webhook_tests.ps1) should
    # seed plans beforehand via:
    #   INSERT INTO subscription_plans (plan_name, price_pennies, seat_limit)
    #   VALUES ('Test Plan', 0, 999)
    return 1


@pytest.fixture(scope="function")
def test_company_id(test_plan_id):
    """Create a test company via API, return company_id, hard-delete after test."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
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
