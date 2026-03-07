import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, get_db
from api.models.message import IncidentScore, Message
from api.models.user import User
from api.schemas.message import IncidentScoreRead, MessageRead

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/stats")
async def message_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Count by severity
    severity_result = await db.execute(
        select(IncidentScore.predicted_severity, func.count())
        .join(Message, IncidentScore.message_id == Message.message_id)
        .where(Message.company_id == user.company_id)
        .group_by(IncidentScore.predicted_severity)
    )
    severity_counts = {row[0] or "unknown": row[1] for row in severity_result.all()}

    # Count by category
    category_result = await db.execute(
        select(IncidentScore.predicted_category, func.count())
        .join(Message, IncidentScore.message_id == Message.message_id)
        .where(Message.company_id == user.company_id)
        .group_by(IncidentScore.predicted_category)
    )
    category_counts = {row[0] or "unknown": row[1] for row in category_result.all()}

    return {"by_severity": severity_counts, "by_category": category_counts}


@router.get("", response_model=list[MessageRead])
async def list_messages(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await db.execute(
        select(Message)
        .where(Message.company_id == user.company_id)
        .order_by(Message.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{message_id}", response_model=MessageRead)
async def get_message(
    message_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message).where(
            Message.message_id == message_id,
            Message.company_id == user.company_id,
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return message
