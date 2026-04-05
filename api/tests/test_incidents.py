import httpx
import pytest
from datetime import datetime, timezone


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


def _me(client: httpx.Client, token: str) -> dict:
    return client.get("/auth/me", headers=_auth(token)).json()


def _incident_payload(user_id: str, source: str = "slack") -> dict:
    return {
        "user_id": user_id,
        "source": source,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "content_raw": {"text": "I can't take this anymore"},
        "conversation_id": "C123",
        "recommendation": "Follow up with user",
    }


def test_create_incident(client: httpx.Client):
    token = _register(client, "inc_create@test.com", "IncCreate Corp")
    me = _me(client, token)
    user_id, company_id = me["user_id"], me["company_id"]

    resp = client.post("/incidents", params={"company_id": company_id}, json=_incident_payload(user_id))
    assert resp.status_code == 201
    body = resp.json()
    assert body["user_id"] == user_id
    assert body["source"] == "slack"
    assert body["content_raw"] == {"text": "I can't take this anymore"}
    assert body["recommendation"] == "Follow up with user"
    assert "message_id" in body


def test_list_incidents(client: httpx.Client):
    token = _register(client, "inc_list@test.com", "IncList Corp")
    me = _me(client, token)
    user_id, company_id = me["user_id"], me["company_id"]

    client.post("/incidents", params={"company_id": company_id}, json=_incident_payload(user_id))
    client.post("/incidents", params={"company_id": company_id}, json=_incident_payload(user_id, source="gmail"))

    resp = client.get("/incidents", headers=_auth(token))
    assert resp.status_code == 200
    incidents = resp.json()
    assert len(incidents) == 2
    sources = {i["source"] for i in incidents}
    assert sources == {"slack", "gmail"}


def test_get_incident_by_id(client: httpx.Client):
    token = _register(client, "inc_get@test.com", "IncGet Corp")
    me = _me(client, token)
    user_id, company_id = me["user_id"], me["company_id"]

    created = client.post("/incidents", params={"company_id": company_id}, json=_incident_payload(user_id)).json()
    message_id = created["message_id"]

    resp = client.get(f"/incidents/{message_id}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["message_id"] == message_id


def test_get_incident_not_found(client: httpx.Client):
    token = _register(client, "inc_notfound@test.com", "IncNotFound Corp")
    fake_id = "00000000-0000-0000-0000-000000000002"
    resp = client.get(f"/incidents/{fake_id}", headers=_auth(token))
    assert resp.status_code == 404


def test_incident_stats(client: httpx.Client):
    token = _register(client, "inc_stats@test.com", "IncStats Corp")
    me = _me(client, token)
    user_id, company_id = me["user_id"], me["company_id"]

    client.post("/incidents", params={"company_id": company_id}, json=_incident_payload(user_id, source="slack"))
    client.post("/incidents", params={"company_id": company_id}, json=_incident_payload(user_id, source="slack"))
    client.post("/incidents", params={"company_id": company_id}, json=_incident_payload(user_id, source="gmail"))

    resp = client.get("/incidents/stats", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["by_source"]["slack"] == 2
    assert body["by_source"]["gmail"] == 1


def test_incident_isolated_between_companies(client: httpx.Client):
    token_a = _register(client, "inc_iso_a@test.com", "IsoA Corp")
    token_b = _register(client, "inc_iso_b@test.com", "IsoB Corp")
    me_a = _me(client, token_a)

    client.post("/incidents", params={"company_id": me_a["company_id"]}, json=_incident_payload(me_a["user_id"]))

    resp = client.get("/incidents", headers=_auth(token_b))
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_create_incident_no_auth_required(client: httpx.Client):
    token = _register(client, "inc_noauth@test.com", "IncNoAuth Corp")
    me = _me(client, token)
    resp = client.post("/incidents", params={"company_id": me["company_id"]}, json=_incident_payload(me["user_id"]))
    assert resp.status_code == 201
