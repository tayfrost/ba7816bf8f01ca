"""
Integration tests for cross-platform account linking.

When a Slack or Gmail account is created with an email that already belongs
to a canonical user (via the other platform), the API must reuse that user_id
rather than creating a duplicate canonical user.

Four cases:
  1. No existing user for this email → passed user_id is used as-is
  2. Gmail-first: mailbox exists → Slack account inherits user_id from mailbox
  3. Slack-first: slack account exists → Gmail mailbox inherits user_id from slack account
  4. Both exist: new account on either platform still resolves to the same user_id
"""

import uuid
import httpx
import pytest


# ── Helpers ───────────────────────────────────────────────────────

def _make_company(client: httpx.Client) -> int:
    resp = client.post("/companies", json={
        "name": f"LinkTest-{uuid.uuid4().hex[:8]}",
        "plan_id": 1,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["company_id"]


def _make_viewer(client: httpx.Client, company_id: int, display_name: str = "Test") -> str:
    resp = client.post("/internal/users/viewer-seat", json={
        "company_id": company_id,
        "display_name": display_name,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["user_id"]


def _make_workspace(client: httpx.Client, company_id: int) -> str:
    team_id = f"T{uuid.uuid4().hex[:8].upper()}"
    resp = client.post("/internal/slack/workspaces", json={
        "company_id": company_id,
        "team_id": team_id,
        "access_token": "xoxb-test",
    })
    assert resp.status_code == 201, resp.text
    return team_id


def _create_slack_account(
    client: httpx.Client,
    company_id: int,
    team_id: str,
    user_id: str,
    email: str | None = None,
    slack_user_id: str | None = None,
) -> httpx.Response:
    return client.post("/internal/slack/accounts", json={
        "company_id":    company_id,
        "team_id":       team_id,
        "slack_user_id": slack_user_id or f"U{uuid.uuid4().hex[:8].upper()}",
        "user_id":       user_id,
        "email":         email,
    })


def _create_mailbox(
    client: httpx.Client,
    company_id: int,
    user_id: str,
    email: str,
) -> httpx.Response:
    return client.post("/internal/mailboxes", json={
        "company_id":    company_id,
        "user_id":       user_id,
        "email_address": email,
        "token_json":    {"token": "t", "refresh_token": "r"},
    })


# ── Tests ─────────────────────────────────────────────────────────

class TestAccountLinking:

    def test_case1_no_existing_user_uses_passed_user_id(self, client: httpx.Client):
        """No account with this email exists anywhere — user_id is used as-is."""
        company_id = _make_company(client)
        user_id    = _make_viewer(client, company_id, "Fresh User")
        team_id    = _make_workspace(client, company_id)
        email      = f"fresh-{uuid.uuid4().hex[:6]}@example.com"

        resp = _create_slack_account(client, company_id, team_id, user_id, email=email)

        assert resp.status_code == 201, resp.text
        assert resp.json()["user_id"] == user_id

    def test_case2_gmail_first_slack_inherits_user_id(self, client: httpx.Client):
        """
        User A registered via Gmail. When a Slack account arrives with the
        same email, it must be linked to user A — not the freshly created seat.
        """
        company_id = _make_company(client)
        email      = f"gmail-first-{uuid.uuid4().hex[:6]}@example.com"

        # User A — created during Gmail OAuth
        user_a = _make_viewer(client, company_id, "Gmail User")
        mb_resp = _create_mailbox(client, company_id, user_a, email)
        assert mb_resp.status_code == 201, mb_resp.text

        # Webhook creates a fresh viewer seat before calling create_slack_account
        user_b  = _make_viewer(client, company_id, "Slack Newcomer")
        team_id = _make_workspace(client, company_id)
        resp    = _create_slack_account(client, company_id, team_id, user_b, email=email)

        assert resp.status_code == 201, resp.text
        # Linking must override user_b with user_a
        assert resp.json()["user_id"] == user_a, (
            f"Expected user_a={user_a}, got {resp.json()['user_id']}"
        )

    def test_case3_slack_first_gmail_inherits_user_id(self, client: httpx.Client):
        """
        User A registered via Slack. When a Gmail mailbox arrives with the
        same email, it must be linked to user A.
        """
        company_id = _make_company(client)
        email      = f"slack-first-{uuid.uuid4().hex[:6]}@example.com"

        # User A — created when first Slack message arrived
        user_a  = _make_viewer(client, company_id, "Slack User")
        team_id = _make_workspace(client, company_id)
        sa_resp = _create_slack_account(client, company_id, team_id, user_a, email=email)
        assert sa_resp.status_code == 201, sa_resp.text

        # Webhook/OAuth creates a fresh viewer seat before calling create_mailbox
        user_b  = _make_viewer(client, company_id, "Gmail Newcomer")
        resp    = _create_mailbox(client, company_id, user_b, email)

        assert resp.status_code == 201, resp.text
        # Linking must override user_b with user_a
        assert resp.json()["user_id"] == user_a, (
            f"Expected user_a={user_a}, got {resp.json()['user_id']}"
        )

    def test_case4_both_exist_new_slack_account_still_links(self, client: httpx.Client):
        """
        User A already has both a Slack account and a Gmail mailbox.
        A second Slack identity (different slack_user_id, same email —
        e.g. reinstall on a second workspace) must still resolve to user A.
        """
        company_id = _make_company(client)
        email      = f"both-{uuid.uuid4().hex[:6]}@example.com"

        # User A — fully linked on both platforms
        user_a   = _make_viewer(client, company_id, "Linked User")
        team_id1 = _make_workspace(client, company_id)
        sa_resp  = _create_slack_account(client, company_id, team_id1, user_a, email=email)
        assert sa_resp.status_code == 201, sa_resp.text
        mb_resp  = _create_mailbox(client, company_id, user_a, email)
        assert mb_resp.status_code == 201, mb_resp.text

        # Second Slack workspace install — fresh viewer seat created by webhook
        user_b   = _make_viewer(client, company_id, "Duplicate Seat")
        team_id2 = _make_workspace(client, company_id)
        resp     = _create_slack_account(client, company_id, team_id2, user_b, email=email)

        assert resp.status_code == 201, resp.text
        # Must resolve back to user_a regardless of which table is found first
        assert resp.json()["user_id"] == user_a, (
            f"Expected user_a={user_a}, got {resp.json()['user_id']}"
        )
