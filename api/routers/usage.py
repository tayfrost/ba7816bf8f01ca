from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import CurrentUser, get_current_user, get_db
from api.models.flagged_incident import FlaggedIncident

router = APIRouter(tags=["usage"])

# Severity weights for risk score calculation.
# Higher weight = more impact on the daily risk score.
SEVERITY_WEIGHTS: dict[str, int] = {
    "suicide": 10,
    "harassment": 8,
    "depression": 7,
    "anxiety": 6,
    "burnout": 5,
    "stress": 3,
}
DEFAULT_WEIGHT = 2


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


def _pretty_label(reason: str) -> str:
    """Turn a class_reason slug into a human-readable label."""
    return reason.replace("_", " ").capitalize()


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    start: str = Query(..., description="Start date ISO format"),
    end: str = Query(..., description="End date ISO format"),
    metrics: str | None = Query(None, description="Comma-separated metric keys"),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)

    requested_metrics = (
        metrics.split(",") if metrics else ["riskScore", "messagesFlagged", "overtimeIndex"]
    )

    # ── Fetch incident data (day + class_reason counts) ────────────
    # This single query powers messagesFlagged, riskScore, and per-reason series.
    result = await db.execute(
        select(
            func.date(FlaggedIncident.created_at).label("day"),
            FlaggedIncident.class_reason,
            func.count().label("cnt"),
        )
        .where(
            FlaggedIncident.company_id == user.company_id,
            FlaggedIncident.created_at >= start_dt,
            FlaggedIncident.created_at <= end_dt,
        )
        .group_by(func.date(FlaggedIncident.created_at), FlaggedIncident.class_reason)
        .order_by(func.date(FlaggedIncident.created_at))
    )
    rows = result.all()

    # ── Organise into lookup structures ────────────────────────────
    # daily_totals: {date_str: total_count}
    daily_totals: dict[str, int] = defaultdict(int)
    # daily_by_reason: {date_str: {reason: count}}
    daily_by_reason: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # all_reasons: set of distinct class_reason values
    all_reasons: set[str] = set()

    for row in rows:
        day_str = str(row.day)
        reason = row.class_reason or "unclassified"
        count = row.cnt

        daily_totals[day_str] += count
        daily_by_reason[day_str][reason] += count
        all_reasons.add(reason)

    sorted_days = sorted(daily_totals.keys())

    series_list: list[Series] = []

    # ── messagesFlagged: total incidents per day ───────────────────
    if "messagesFlagged" in requested_metrics:
        points = [SeriesPoint(date=d, value=daily_totals[d]) for d in sorted_days]
        series_list.append(
            Series(key="messagesFlagged", label="Messages flagged", points=points)
        )

    # ── riskScore: weighted severity score per day (0-100) ─────────
    if "riskScore" in requested_metrics:
        risk_points = []
        for day in sorted_days:
            weighted_sum = 0
            for reason, count in daily_by_reason[day].items():
                weight = SEVERITY_WEIGHTS.get(reason, DEFAULT_WEIGHT)
                weighted_sum += weight * count
            # Cap at 100
            score = min(100, weighted_sum)
            risk_points.append(SeriesPoint(date=day, value=score))
        series_list.append(
            Series(key="riskScore", label="Risk score", points=risk_points)
        )

    # ── Per-reason breakdown: one series per class_reason ──────────
    for reason in sorted(all_reasons):
        reason_key = reason.replace(" ", "_").lower()
        if reason_key in requested_metrics or not metrics:
            points = []
            for day in sorted_days:
                value = daily_by_reason[day].get(reason, 0)
                points.append(SeriesPoint(date=day, value=value))
            series_list.append(
                Series(key=reason_key, label=_pretty_label(reason), points=points)
            )

    # ── overtimeIndex: placeholder ─────────────────────────────────
    if "overtimeIndex" in requested_metrics:
        series_list.append(
            Series(key="overtimeIndex", label="Overtime index", points=[])
        )

    return UsageResponse(
        range={"start": start, "end": end},
        series=series_list,
    )
