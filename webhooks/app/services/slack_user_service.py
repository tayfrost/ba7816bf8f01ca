"""
Slack User Service

Fetches user profile data (name, email) from the Slack Web API
using the workspace bot token and the users:read scope.
"""

import logging
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

SLACK_USERS_INFO_URL = "https://slack.com/api/users.info"


def lookup_slack_user(
    access_token: str, slack_user_id: str
) -> Tuple[str, str, Optional[str]]:
    """
    Call Slack's users.info API to retrieve a user's real name and email.

    Args:
        access_token: Bot/user OAuth token with users:read (and ideally users:read.email)
        slack_user_id: The Slack user ID (e.g. U01ABC123)

    Returns:
        (first_name, last_name, email) — email may be None if the
        users:read.email scope is not granted or the user has no email set.
    """
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                SLACK_USERS_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"user": slack_user_id},
            )
            data = resp.json()

        if not data.get("ok"):
            logger.warning(
                f"Slack users.info failed for {slack_user_id}: {data.get('error')}"
            )
            return "unknown", "unknown", None

        profile = data["user"].get("profile", {})

        first_name = (
            profile.get("first_name")
            or data["user"].get("real_name", "unknown").split()[0]
        )
        last_name = (
            profile.get("last_name")
            or (data["user"].get("real_name", "").split()[1:]
                and " ".join(data["user"]["real_name"].split()[1:]))
            or "unknown"
        )
        email = profile.get("email")

        return first_name, last_name, email

    except httpx.TimeoutException:
        logger.error(f"Slack users.info timed out for {slack_user_id}")
        return "unknown", "unknown", None
    except Exception as e:
        logger.error(f"Slack users.info unexpected error for {slack_user_id}: {e}")
        return "unknown", "unknown", None
