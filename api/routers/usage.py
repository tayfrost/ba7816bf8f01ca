import asyncio
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_current_user
from database.db_service.utils import crud_incident_scores
from database.db_service.utils import crud_message_incidents

router = APIRouter(tags=["usage"])

SEVERITY_WEIGHTS: dict[str, float] = {
    "suicidal_ideation": 10.0,
    "harassment": 8.0,
    "depression": 7.0,
    "burnout": 5.0,
    "stress": 3.0,
    "humor_sarcasm": 1.0,
    "neutral": 0.0,
}


class SeriesPoint(BaseModel):
    date: str
    value: float


class Series(BaseModel):
    key: str
    label: str
    points: list[SeriesPoint]


class UsageResponse(BaseModel):
    range: dict
    series: list[Series]


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    start: str = Query(..., description="Start date ISO format"),
    end: str = Query(..., description="End date ISO format"),
    metrics: str | None = Query(None, description="Comma-separated metric keys"),
    user: CurrentUser = Depends(get_current_user),
):
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    requested_metrics = (
        metrics.split(",") if metrics else ["riskScore", "messagesFlagged", "overtimeIndex"]
    )

    incidents = await asyncio.to_thread(
        crud_message_incidents.list_message_incidents_for_company,
        user.company_id, limit=10000,
    )

    # Filter by date range (normalize to naive for comparison)
    def _naive(dt: datetime) -> datetime:
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    incidents = [i for i in incidents if start_dt <= _naive(i.sent_at) <= end_dt]

    daily_totals: dict[str, int] = defaultdict(int)
    daily_risk: dict[str, float] = defaultdict(float)
    daily_by_source: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for inc in incidents:
        day_str = _naive(inc.sent_at).date().isoformat()
        daily_totals[day_str] += 1
        daily_by_source[day_str][inc.source] += 1

        scores = await asyncio.to_thread(
            crud_incident_scores.get_incident_scores_by_message_id, inc.message_id
        )
        if scores:
            risk = (
                scores.suicidal_ideation_score * SEVERITY_WEIGHTS["suicidal_ideation"]
                + scores.harassment_score * SEVERITY_WEIGHTS["harassment"]
                + scores.depression_score * SEVERITY_WEIGHTS["depression"]
                + scores.burnout_score * SEVERITY_WEIGHTS["burnout"]
                + scores.stress_score * SEVERITY_WEIGHTS["stress"]
            )
            daily_risk[day_str] += risk

    sorted_days = sorted(daily_totals.keys())
    series_list: list[Series] = []

    if "messagesFlagged" in requested_metrics:
        series_list.append(Series(
            key="messagesFlagged", label="Messages flagged",
            points=[SeriesPoint(date=d, value=daily_totals[d]) for d in sorted_days],
        ))

    if "riskScore" in requested_metrics:
        series_list.append(Series(
            key="riskScore", label="Risk score",
            points=[SeriesPoint(date=d, value=min(100.0, daily_risk[d])) for d in sorted_days],
        ))

    for source in ["slack", "gmail"]:
        if not metrics or source in requested_metrics:
            series_list.append(Series(
                key=source, label=source.capitalize(),
                points=[SeriesPoint(date=d, value=daily_by_source[d].get(source, 0)) for d in sorted_days],
            ))

    if "overtimeIndex" in requested_metrics:
        series_list.append(Series(key="overtimeIndex", label="Overtime index", points=[]))

    return UsageResponse(range={"start": start, "end": end}, series=series_list)
