"""
Slack User Service

Fetches user profile data (name, email) from the Slack Web API
using the workspace bot token and the users:read + users:read.email scopes.

Includes a TTL cache to avoid redundant API calls for the same user
(e.g. a user sends multiple flagged messages in quick succession).
"""

import logging
from time import time
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

SLACK_USERS_INFO_URL = "https://slack.com/api/users.info"

_TIMEOUT = 1.5

_DEFAULT = ("unknown", "unknown", None)

_cache: dict[str, Tuple[str, str, Optional[str], float]] = {}
_CACHE_TTL = 300  # 5 minutes


def _parse_name(user: dict) -> Tuple[str, str]:
    """Extract first/last name from Slack user object, safely handling single-word names."""
    profile = user.get("profile", {})

    first = profile.get("first_name") or ""
    last = profile.get("last_name") or ""

    if first and last:
        return first, last

    real_name = user.get("real_name", "")
    if real_name:
        parts = real_name.split(None, 1)
        first = first or parts[0]
        last = last or (parts[1] if len(parts) > 1 else "unknown")
        return first, last

    return first or "unknown", last or "unknown"


def lookup_slack_user(
    access_token: str, slack_user_id: str
) -> Tuple[str, str, Optional[str]]:
    """
    Call Slack's users.info API to retrieve a user's real name and email.

    Results are cached for 5 minutes per user ID to avoid redundant API
    calls and stay within Slack's Tier 4 rate limit (~100 req/min).

    Args:
        access_token: Bot OAuth token with users:read (+ users:read.email for email)
        slack_user_id: The Slack user ID (e.g. U01ABC123)

    Returns:
        (first_name, last_name, email) — email is None if the
        users:read.email scope is missing, user has no email, or API errors.
    """
    if slack_user_id in _cache:
        first, last, email, ts = _cache[slack_user_id]
        if time() - ts < _CACHE_TTL:
            return first, last, email

    result = _fetch_from_slack(access_token, slack_user_id)
    if result != _DEFAULT:
        _cache[slack_user_id] = (*result, time())
    return result


def _fetch_from_slack(
    access_token: str, slack_user_id: str
) -> Tuple[str, str, Optional[str]]:
    """Raw API call — callers should go through lookup_slack_user() for caching."""
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(
                SLACK_USERS_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"user": slack_user_id},
            )
            resp.raise_for_status()
            data = resp.json()

        if not data.get("ok"):
            logger.warning(
                f"Slack users.info failed for {slack_user_id}: {data.get('error')}"
            )
            return _DEFAULT

        user = data.get("user", {})
        first_name, last_name = _parse_name(user)
        email = user.get("profile", {}).get("email") or None

        return first_name, last_name, email

    except httpx.TimeoutException:
        logger.error(f"Slack users.info timed out for {slack_user_id}")
        return _DEFAULT
    except httpx.HTTPStatusError as e:
        logger.warning(f"Slack users.info HTTP {e.response.status_code} for {slack_user_id}")
        return _DEFAULT
    except (ValueError, KeyError) as e:
        logger.warning(f"Slack users.info malformed response for {slack_user_id}: {e}")
        return _DEFAULT
    except Exception as e:
        logger.error(f"Slack users.info unexpected error for {slack_user_id}: {e}")
        return _DEFAULT
