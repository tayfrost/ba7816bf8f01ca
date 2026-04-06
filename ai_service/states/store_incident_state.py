"""Database storage state node for the mental health assessment workflow."""

import os
import logging
import json
import httpx
from schema.agent_state import AgentState

logger = logging.getLogger(__name__)

INTERNAL_API_URL = os.getenv("INTERNAL_API_URL", "http://api:8000")


async def store_incident(state: AgentState) -> AgentState:
    logger.info("[NODE: store_incident] Starting database storage")

    hr_report = state.get("hr_report", {})
    content_to_store = {
        "text": state.get("raw_message", ""),
        "filter_category": state.get("filter_category"),
        "filter_severity": state.get("filter_severity"),
        "ai_analysis": hr_report.get("response", "")
    }

    recommendations_list = hr_report.get("recommendations", [])
    recommendation_str = json.dumps(recommendations_list) if recommendations_list else None

    payload = {
        "user_id": str(state["user_id"]),
        "source": state["source"],
        "sent_at": state["sent_at"].isoformat() if hasattr(state["sent_at"], "isoformat") else state["sent_at"],
        "content_raw": content_to_store,
        "conversation_id": state.get("conversation_id"),
        "recommendation": recommendation_str,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{INTERNAL_API_URL}/internal/incidents",
                params={"company_id": state["company_id"]},
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()

        message_id = response.json().get("message_id")
        logger.info(f"[NODE: store_incident] Successfully stored incident {message_id}")

    except Exception as e:
        logger.error(f"[NODE: store_incident] Failed to store incident: {e}", exc_info=True)
        raise

    return state
