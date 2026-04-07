"""Database storage state node for the mental health assessment workflow."""

import os
import logging
import json
import httpx
from schema.agent_state import AgentState

logger = logging.getLogger(__name__)

INTERNAL_API_URL = os.getenv("INTERNAL_API_URL", "http://api:8000")

_SEVERITY_MAP = {"low": 1, "medium": 2, "high": 3}


def _build_scores_payload(state: AgentState) -> dict:
    """Map LLM grades and filter output to incident_scores columns."""
    hr_report = state.get("hr_report") or {}
    grades = hr_report.get("scores") or {}

    def _norm(key: str) -> float:
        """Normalise a 0-100 LLM grade to 0.0-1.0."""
        return min(1.0, max(0.0, float(grades.get(key, 0)) / 100.0))

    stress      = _norm("stress_level")
    suicidal    = _norm("suicide_risk")
    burnout     = _norm("burnout_score")
    depression  = _norm("depression_indicators")
    harassment  = _norm("anxiety_markers")
    neutral     = round(max(0.0, 1.0 - max(stress, suicidal, burnout, depression, harassment)), 4)

    severity_str = str(state.get("filter_severity", "")).lower()

    return {
        "neutral_score":           neutral,
        "humor_sarcasm_score":     0.0,
        "stress_score":            round(stress, 4),
        "burnout_score":           round(burnout, 4),
        "depression_score":        round(depression, 4),
        "harassment_score":        round(harassment, 4),
        "suicidal_ideation_score": round(suicidal, 4),
        "predicted_category":      state.get("filter_category"),
        "predicted_severity":      _SEVERITY_MAP.get(severity_str),
    }


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

    message_id = None
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

    if message_id:
        try:
            scores_payload = _build_scores_payload(state)
            async with httpx.AsyncClient() as client:
                scores_resp = await client.post(
                    f"{INTERNAL_API_URL}/internal/incidents/{message_id}/scores",
                    json=scores_payload,
                    timeout=10.0,
                )
                scores_resp.raise_for_status()
            logger.info(f"[NODE: store_incident] Stored scores for {message_id}")
        except Exception as e:
            logger.error(f"[NODE: store_incident] Failed to store scores: {e}", exc_info=True)

    return state
