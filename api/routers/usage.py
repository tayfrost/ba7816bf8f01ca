import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_current_user
from database.services import crud_incident_scores

router = APIRouter(tags=["usage"])

SCORE_CATEGORIES = [
    ("depression", "Depression"),
    ("burnout", "Burnout"),
    ("stress", "Stress"),
    ("harassment", "Harassment"),
    ("suicidal_ideation", "Suicidal ideation"),
]


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


def _rolling_average(points: list[SeriesPoint], window: int = 3) -> list[SeriesPoint]:
    """Server-side rolling average over `window` days."""
    result = []
    for i, p in enumerate(points):
        chunk = points[max(0, i - window + 1): i + 1]
        avg = sum(c.value for c in chunk) / len(chunk)
        result.append(SeriesPoint(date=p.date, value=round(avg, 4)))
    return result


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    start: str = Query(..., description="Start date ISO format"),
    end: str = Query(..., description="End date ISO format"),
    metrics: str | None = Query(None, description="Comma-separated metric keys (ignored; all score categories always returned)"),
    user: CurrentUser = Depends(get_current_user),
):
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)

    rows = await asyncio.to_thread(
        crud_incident_scores.list_daily_score_averages,
        user.company_id, start_dt, end_dt,
    )

    # Build a point list per category
    category_points: dict[str, list[SeriesPoint]] = {key: [] for key, _ in SCORE_CATEGORIES}
    for row in rows:
        day_str = row["day"].isoformat() if hasattr(row["day"], "isoformat") else str(row["day"])
        for key, _ in SCORE_CATEGORIES:
            category_points[key].append(SeriesPoint(date=day_str, value=row[key]))

    series_list: list[Series] = [
        Series(
            key=key,
            label=label,
            points=_rolling_average(category_points[key]),
        )
        for key, label in SCORE_CATEGORIES
    ]

    return UsageResponse(range={"start": start, "end": end}, series=series_list)
