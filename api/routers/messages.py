import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import CurrentUser, get_current_user, require_role
from api.schemas.incident import MessageIncidentCreate, MessageIncidentRead
from database.services import crud_message_incidents

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("/stats")
async def incident_stats(user: CurrentUser = Depends(get_current_user)):
    incidents = await asyncio.to_thread(
        crud_message_incidents.list_message_incidents_for_company,
        user.company_id, limit=10000,
    )
    by_source: dict[str, int] = {}
    for inc in incidents:
        by_source[inc.source] = by_source.get(inc.source, 0) + 1
    return {"total": len(incidents), "by_source": by_source}


@router.get("", response_model=list[MessageIncidentRead])
async def list_incidents(
    user: CurrentUser = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return await asyncio.to_thread(
        crud_message_incidents.list_message_incidents_for_company,
        user.company_id, limit=limit, offset=skip,
    )


@router.get("/{incident_id}", response_model=MessageIncidentRead)
async def get_incident(
    incident_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
):
    incident = await asyncio.to_thread(
        crud_message_incidents.get_message_incident_by_id, incident_id
    )
    if not incident or incident.company_id != user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


@router.post("", response_model=MessageIncidentRead, status_code=status.HTTP_201_CREATED)
async def create_incident(company_id: int, body: MessageIncidentCreate):
    try:
        return await asyncio.to_thread(
            crud_message_incidents.create_message_incident,
            company_id,
            user_id=body.user_id,
            source=body.source,
            sent_at=body.sent_at,
            content_raw=body.content_raw,
            conversation_id=body.conversation_id,
            recommendation=body.recommendation,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
