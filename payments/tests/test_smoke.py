import sys
from pathlib import Path

from pydantic import ValidationError

sys.path.append(str(Path(__file__).resolve().parents[2]))


def test_payments_app_routes_load(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/sentinelai",
    )

    from payments.app.main import app

    paths = {route.path for route in app.routes}

    assert "/health" in paths
    assert "/api/v1/plans" in paths
    assert "/api/v1/checkout" in paths
    assert "/api/v1/webhooks/stripe" in paths


def test_payments_env_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from payments.app.core.config import get_settings

    get_settings.cache_clear()
    try:
        raised = False
        try:
            get_settings()
        except ValidationError:
            raised = True
        assert raised is True
    finally:
        get_settings.cache_clear()
