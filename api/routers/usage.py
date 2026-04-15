import asyncio
from datetime import date, datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_current_user
from database.services import crud_incident_scores

router = APIRouter(tags=["usage"])
logger = logging.getLogger(__name__)

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
    # Treat `end` as inclusive calendar day by querying up to next midnight.
    end_dt = datetime.fromisoformat(end) + timedelta(days=1)

    logger.info(
        "[usage] request company_id=%s start=%s end=%s effective_end_exclusive=%s",
        user.company_id,
        start,
        end,
        end_dt.isoformat(),
    )

    rows = await asyncio.to_thread(
        crud_incident_scores.list_daily_score_averages,
        user.company_id, start_dt, end_dt,
    )

    logger.info("[usage] rows_returned=%d", len(rows))
    if rows:
        logger.info("[usage] first_row=%s", rows[0])
        logger.info("[usage] last_row=%s", rows[-1])

    # Build a full date spine from start to min(end, today), filling quiet days with 0
    today = datetime.now(timezone.utc).date()
    spine_end = min(end_dt.date(), today)
    spine_start = start_dt.date()
    all_days: list[date] = []
    d = spine_start
    while d <= spine_end:
        all_days.append(d)
        d += timedelta(days=1)

    row_by_day = {
        (row["day"] if isinstance(row["day"], date) else row["day"].date()): row
        for row in rows
    }

    category_points: dict[str, list[SeriesPoint]] = {key: [] for key, _ in SCORE_CATEGORIES}
    for day in all_days:
        row = row_by_day.get(day)
        day_str = day.isoformat()
        for key, _ in SCORE_CATEGORIES:
            category_points[key].append(SeriesPoint(date=day_str, value=float(row[key]) if row else 0.0))

    series_list: list[Series] = [
        Series(
            key=key,
            label=label,
            points=_rolling_average(category_points[key]),
        )
        for key, label in SCORE_CATEGORIES
    ]

    logger.info(
        "[usage] series_points=%s",
        {s.key: len(s.points) for s in series_list},
    )

    return UsageResponse(range={"start": start, "end": end}, series=series_list)
