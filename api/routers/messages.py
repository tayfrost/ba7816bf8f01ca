from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import CurrentUser, get_current_user, get_db
from api.models.flagged_incident import FlaggedIncident
from api.schemas.incident import FlaggedIncidentRead

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("/stats")
async def incident_stats(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Count by class_reason
    result = await db.execute(
        select(FlaggedIncident.class_reason, func.count())
        .where(FlaggedIncident.company_id == user.company_id)
        .group_by(FlaggedIncident.class_reason)
    )
    reason_counts = {row[0] or "unknown": row[1] for row in result.all()}

    total = sum(reason_counts.values())
    return {"total": total, "by_reason": reason_counts}


@router.get("", response_model=list[FlaggedIncidentRead])
async def list_incidents(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await db.execute(
        select(FlaggedIncident)
        .where(FlaggedIncident.company_id == user.company_id)
        .order_by(FlaggedIncident.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{incident_id}", response_model=FlaggedIncidentRead)
async def get_incident(
    incident_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FlaggedIncident).where(
            FlaggedIncident.incident_id == incident_id,
            FlaggedIncident.company_id == user.company_id,
        )
    )
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident
