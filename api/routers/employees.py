import asyncio
import math
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_current_user
from database.services import (
    users_crud,
    crud_slack_accounts,
    crud_google_mailboxes,
    crud_message_incidents,
)

router = APIRouter(prefix="/employees", tags=["employees"])

CATEGORY_WEIGHTS: dict[str, float] = {
    "suicidal_ideation": 10.0,
    "harassment": 8.0,
    "depression": 7.0,
    "burnout": 5.0,
    "stress": 3.0,
    "humor_sarcasm": 1.0,
    "neutral": 0.0,
}


class TrendPoint(BaseModel):
    date: str
    value: float


class EmployeeItem(BaseModel):
    id: str
    fullName: str
    role: str
    team: str
    email: str
    source: list[str]
    riskScore: int
    flaggedCount: int
    overtimeHours: int
    lastActive: str
    status: str
    trend: list[TrendPoint]


class EmployeesResponse(BaseModel):
    employees: list[EmployeeItem]


def _moving_average(values: list[float], window: int = 7) -> list[float]:
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        chunk = values[start : i + 1]
        result.append(sum(chunk) / len(chunk))
    return result


def _derive_status(risk_score: int) -> str:
    if risk_score >= 85:
        return "critical"
    if risk_score >= 45:
        return "watchlist"
    return "active"


def _build_trend(incident_list: list, days: int = 30, ma_window: int = 7) -> list[TrendPoint]:
    """
    Daily weighted risk score (0-100) with log dampening and moving average.

    Each day's score = log-damped average of category weights across all incidents:
      score = min(100, avg_weight * log2(1 + n) * 10)
    where n is the incident count for that day.
    This means more incidents push the score up, but diminishingly.
    """
    now = datetime.now(tz=timezone.utc)
    start = now - timedelta(days=days - 1)

    daily_weight_sum: dict[str, float] = {
        (start + timedelta(days=d)).date().isoformat(): 0.0
        for d in range(days)
    }
    daily_count: dict[str, int] = {
        (start + timedelta(days=d)).date().isoformat(): 0
        for d in range(days)
    }

    for inc in incident_list:
        sent = inc.sent_at
        if sent.tzinfo is None:
            sent = sent.replace(tzinfo=timezone.utc)
        if sent < start:
            continue
        day = sent.date().isoformat()
        if day in daily_weight_sum:
            category = (inc.content_raw or {}).get("filter_category") or "neutral"
            daily_weight_sum[day] += CATEGORY_WEIGHTS.get(category, 0.0)
            daily_count[day] += 1

    sorted_days = sorted(daily_weight_sum)

    # Apply log dampening per day before moving average
    dampened: list[float] = []
    for d in sorted_days:
        n = daily_count[d]
        raw_sum = daily_weight_sum[d]
        if n > 0:
            avg_weight = raw_sum / n
            dampened.append(avg_weight * math.log2(1 + n))
        else:
            dampened.append(0.0)

    smoothed = _moving_average(dampened, ma_window)

    return [
        TrendPoint(date=d, value=round(min(100.0, v * 10), 1))
        for d, v in zip(sorted_days, smoothed)
    ]


@router.get("", response_model=EmployeesResponse)
async def list_employees(user: CurrentUser = Depends(get_current_user)):
    users, slack_accounts, mailboxes, all_incidents = await asyncio.gather(
        asyncio.to_thread(users_crud.list_users, user.company_id),
        asyncio.to_thread(
            crud_slack_accounts.list_slack_accounts_for_company,
            user.company_id, limit=10000,
        ),
        asyncio.to_thread(
            crud_google_mailboxes.list_google_mailboxes_for_company,
            user.company_id,
        ),
        asyncio.to_thread(
            crud_message_incidents.list_message_incidents_for_company,
            user.company_id, limit=10000,
        ),
    )

    slack_by_user: dict[str, list] = defaultdict(list)
    for a in slack_accounts:
        slack_by_user[str(a.user_id)].append(a)

    mailbox_by_user: dict[str, list] = defaultdict(list)
    for m in mailboxes:
        mailbox_by_user[str(m.user_id)].append(m)

    incidents_by_user: dict[str, list] = defaultdict(list)
    for inc in all_incidents:
        incidents_by_user[str(inc.user_id)].append(inc)

    # Only monitored employees (viewers) are shown; admin/biller seats are excluded.
    viewer_users = [u for u in users if u.role == "viewer"]

    employees: list[EmployeeItem] = []
    for u in viewer_users:
        uid_str = str(u.user_id)
        user_incidents = incidents_by_user.get(uid_str, [])
        user_slacks = slack_by_user.get(uid_str, [])
        user_mailboxes = mailbox_by_user.get(uid_str, [])

        sources: list[str] = []
        if user_slacks:
            sources.append("slack")
        if user_mailboxes:
            sources.append("gmail")

        if user_slacks:
            team = user_slacks[0].team_id
            email = user_slacks[0].email or ""
        elif user_mailboxes:
            team = "gmail"
            email = user_mailboxes[0].email_address
        else:
            team = "N/A"
            email = ""

        flagged_count = len(user_incidents)

        if flagged_count > 0:
            total_weight = sum(
                CATEGORY_WEIGHTS.get(
                    (inc.content_raw or {}).get("filter_category") or "neutral", 0.0
                )
                for inc in user_incidents
            )
            risk_score = min(100, int((total_weight / flagged_count) * 10))
            last_active = max(inc.sent_at for inc in user_incidents)
            last_active_str = last_active.isoformat()
        else:
            risk_score = 0
            last_active_str = ""

        employees.append(EmployeeItem(
            id=uid_str,
            fullName=u.display_name or email or f"User {uid_str[:8]}",
            role=u.role,
            team=team,
            email=email,
            source=sources,
            riskScore=risk_score,
            flaggedCount=flagged_count,
            overtimeHours=0,
            lastActive=last_active_str,
            status=_derive_status(risk_score),
            trend=_build_trend(user_incidents),
        ))

    employees.sort(key=lambda e: e.riskScore, reverse=True)
    return EmployeesResponse(employees=employees)
