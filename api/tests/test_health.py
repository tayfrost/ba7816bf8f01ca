import httpx


def test_health_check(client: httpx.Client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_direct():
    """Direct HTTP call to the container — no fixture dependency."""
    response = httpx.get("http://localhost:8006/health", timeout=10.0)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
