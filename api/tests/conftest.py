"""
Container integration test configuration.
Tests hit the real API at http://localhost:8006 backed by pgvector at localhost:5433.
"""
import psycopg
import pytest
import httpx

BASE_URL = "http://localhost:8006"
DB_DSN = "postgresql://postgres:postgres@localhost:5433/sentinelai"

TRUNCATE_SQL = """
    TRUNCATE
        auth_users,
        slack_accounts,
        google_mailboxes,
        message_incidents,
        incident_scores,
        slack_workspaces,
        subscriptions,
        users,
        companies,
        subscription_plans
    RESTART IDENTITY CASCADE
"""


@pytest.fixture(scope="session", autouse=True)
def seed_db():
    """Clean slate + seed plan_id=1 before the test session."""
    with psycopg.connect(DB_DSN, autocommit=True) as conn:
        conn.execute(TRUNCATE_SQL)
        conn.execute(
            "INSERT INTO subscription_plans (plan_name, price_pennies, currency, seat_limit) "
            "VALUES ('Free', 0, 'GBP', 10)"
        )
    yield
    with psycopg.connect(DB_DSN, autocommit=True) as conn:
        conn.execute(TRUNCATE_SQL)


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c
