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


def test_list_users_includes_self(client: httpx.Client):
    token = _register(client, "userlist@test.com", "UserList Corp")
    resp = client.get("/users", headers=_auth(token))
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) == 1
    assert users[0]["email"] == "userlist@test.com"
    assert users[0]["role"] == "biller"


def test_get_user_by_id(client: httpx.Client):
    token = _register(client, "getuser@test.com", "GetUser Corp")
    me = client.get("/auth/me", headers=_auth(token)).json()
    user_id = me["user_id"]

    resp = client.get(f"/users/{user_id}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["user_id"] == user_id
    assert resp.json()["email"] == "getuser@test.com"


def test_get_user_not_found(client: httpx.Client):
    token = _register(client, "usernotfound@test.com", "UserNotFound Corp")
    fake_id = "00000000-0000-0000-0000-000000000001"
    resp = client.get(f"/users/{fake_id}", headers=_auth(token))
    assert resp.status_code == 404


def test_invite_user(client: httpx.Client):
    token = _register(client, "inviter@test.com", "Invite Corp")
    company_id = client.get("/auth/me", headers=_auth(token)).json()["company_id"]
    resp = client.post(
        "/users/invite",
        params={"company_id": company_id, "email": "invitee@test.com", "role": "viewer", "display_name": "Invited"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "invitee@test.com"
    assert body["role"] == "viewer"

    users = client.get("/users", headers=_auth(token)).json()
    assert len(users) == 2


def test_update_user_display_name_and_role(client: httpx.Client):
    token = _register(client, "upduser@test.com", "UpdUser Corp")
    me = client.get("/auth/me", headers=_auth(token)).json()
    user_id = me["user_id"]

    resp = client.patch(
        f"/users/{user_id}",
        json={"display_name": "Updated Name", "role": "admin"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Updated Name"
    assert body["role"] == "admin"


def test_deactivate_user(client: httpx.Client):
    token = _register(client, "deacuser@test.com", "DeacUser Corp")
    company_id = client.get("/auth/me", headers=_auth(token)).json()["company_id"]

    # invite a second user to deactivate
    invite_resp = client.post(
        "/users/invite",
        params={"company_id": company_id, "email": "victim@test.com", "role": "viewer"},
        headers=_auth(token),
    )
    assert invite_resp.status_code == 201
    victim_id = invite_resp.json()["user_id"]

    resp = client.delete(f"/users/{victim_id}", headers=_auth(token))
    assert resp.status_code == 200

    # deactivated user should not appear in list (soft delete)
    users = client.get("/users", headers=_auth(token)).json()
    ids = [u["user_id"] for u in users]
    assert victim_id not in ids


def test_invite_requires_auth(client: httpx.Client):
    token = _register(client, "invite_noauth@test.com", "InviteNoAuth Corp")
    company_id = client.get("/auth/me", headers=_auth(token)).json()["company_id"]
    resp = client.post("/users/invite", params={"company_id": company_id, "email": "noauth_invitee@test.com"})
    assert resp.status_code == 401
