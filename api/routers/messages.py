import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import CurrentUser, get_current_user, require_role
from api.schemas.incident import (
    MessageIncidentCreate,
    MessageIncidentRead,
    IncidentFeedItem,
    IncidentFeedStats,
)
from database.services import (
    crud_message_incidents,
    crud_slack_accounts,
    crud_google_mailboxes,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _build_feed_items(
    incidents: list,
    skip: int,
    slack_by_user: dict,
    mailbox_by_user: dict,
) -> list[IncidentFeedItem]:
    items = []
    for idx, inc in enumerate(incidents, start=skip + 1):
        uid_str = str(inc.user_id)
        slack = slack_by_user.get(uid_str)
        mailbox = mailbox_by_user.get(uid_str)

        if slack:
            team_id = slack.team_id
            slack_user_id = slack.slack_user_id
        elif mailbox:
            team_id = "gmail"
            slack_user_id = mailbox.email_address
        else:
            team_id = inc.source
            slack_user_id = uid_str

        content = inc.content_raw or {}
        text = content.get("text", "")

        items.append(IncidentFeedItem(
            incident_id=idx,
            company_id=inc.company_id,
            team_id=team_id,
            slack_user_id=slack_user_id,
            message_ts=inc.sent_at.isoformat(),
            created_at=inc.created_at.isoformat(),
            channel_id=inc.conversation_id or inc.source,
            raw_message_text={"text": text} if text else None,
            class_reason=content.get("filter_category") or "unknown",
            recommendation=inc.recommendation,
        ))
    return items


@router.get("/stats", response_model=IncidentFeedStats)
async def incident_stats(user: CurrentUser = Depends(get_current_user)):
    incidents = await asyncio.to_thread(
        crud_message_incidents.list_message_incidents_for_company,
        user.company_id, limit=10000,
    )
    by_reason: dict[str, int] = {}
    for inc in incidents:
        category = (inc.content_raw or {}).get("filter_category") or "unknown"
        by_reason[category] = by_reason.get(category, 0) + 1
    return IncidentFeedStats(total=len(incidents), by_reason=by_reason)


@router.get("", response_model=list[IncidentFeedItem])
async def list_incidents(
    user: CurrentUser = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    incidents, slack_accounts, mailboxes = await asyncio.gather(
        asyncio.to_thread(
            crud_message_incidents.list_message_incidents_for_company,
            user.company_id, limit=limit, offset=skip,
        ),
        asyncio.to_thread(
            crud_slack_accounts.list_slack_accounts_for_company,
            user.company_id, limit=10000,
        ),
        asyncio.to_thread(
            crud_google_mailboxes.list_google_mailboxes_for_company,
            user.company_id,
        ),
    )

    slack_by_user = {str(a.user_id): a for a in slack_accounts}
    mailbox_by_user = {str(m.user_id): m for m in mailboxes}

    return _build_feed_items(incidents, skip, slack_by_user, mailbox_by_user)


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
