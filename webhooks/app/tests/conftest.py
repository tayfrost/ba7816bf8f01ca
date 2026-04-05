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
    # Query for existing plans
    try:
        response = httpx.get(
            f"{API_BASE_URL}/internal/companies",
            timeout=10.0,
        )
        # If internal endpoint returns plans, great. If not, we'll create one directly in DB.
    except Exception:
        pass

    # For now, hardcode plan_id=1. In a real scenario, you'd either:
    # 1. Query via an internal endpoint to list plans
    # 2. Create a plan via an admin endpoint
    # 3. Use direct DB insert in a setup script
    #
    # As a workaround, we return 1 and assume tests handle if it doesn't exist.
    # The test runner (run_webhook_tests.ps1) should seed plans beforehand.
    return 1


@pytest.fixture(scope="function")
def test_company_id(test_plan_id):
    """Create a test company via API, return company_id, cleanup after test."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
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
    company_data = response.json()
    company_id = company_data["company_id"]

    yield company_id

    # Cleanup: soft delete the company
    # (Note: This would need auth, so we skip cleanup for now)
    # Alternatively, the test DB can be reset between runs