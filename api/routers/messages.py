from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import CurrentUser, get_current_user, get_db, require_role
from api.models.flagged_incident import FlaggedIncident
from api.schemas.incident import FlaggedIncidentCreate, FlaggedIncidentRead

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


@router.post("", response_model=FlaggedIncidentRead, status_code=status.HTTP_201_CREATED)
async def create_incident(
    body: FlaggedIncidentCreate,
    user: CurrentUser = Depends(require_role("admin", "biller")),
    db: AsyncSession = Depends(get_db),
):
    incident = FlaggedIncident(
        company_id=user.company_id,
        team_id=body.team_id,
        slack_user_id=body.slack_user_id,
        message_ts=body.message_ts,
        channel_id=body.channel_id,
        raw_message_text=body.raw_message_text,
        class_reason=body.class_reason,
        recommendation=body.recommendation,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return incident
