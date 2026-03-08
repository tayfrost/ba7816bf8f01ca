from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import CurrentUser, get_current_user, get_db
from api.models.flagged_incident import FlaggedIncident

router = APIRouter(tags=["usage"])


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
    db: AsyncSession = Depends(get_db),
):
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)

    requested_metrics = metrics.split(",") if metrics else ["riskScore", "messagesFlagged", "overtimeIndex"]
    series_list = []

    if "messagesFlagged" in requested_metrics:
        # Count flagged incidents per day
        result = await db.execute(
            select(
                func.date(FlaggedIncident.created_at).label("day"),
                func.count().label("cnt"),
            )
            .where(
                FlaggedIncident.company_id == user.company_id,
                FlaggedIncident.created_at >= start_dt,
                FlaggedIncident.created_at <= end_dt,
            )
            .group_by(func.date(FlaggedIncident.created_at))
            .order_by(func.date(FlaggedIncident.created_at))
        )
        points = [SeriesPoint(date=str(row.day), value=row.cnt) for row in result.all()]
        series_list.append(Series(key="messagesFlagged", label="Messages flagged", points=points))

    if "riskScore" in requested_metrics:
        # Placeholder — risk scoring from class_reason not yet quantified
        series_list.append(Series(key="riskScore", label="Risk score", points=[]))

    if "overtimeIndex" in requested_metrics:
        # Placeholder — overtime tracking not yet implemented
        series_list.append(Series(key="overtimeIndex", label="Overtime index", points=[]))

    return UsageResponse(
        range={"start": start, "end": end},
        series=series_list,
    )
