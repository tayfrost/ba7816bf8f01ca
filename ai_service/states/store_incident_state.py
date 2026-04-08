"""Database storage state node for the mental health assessment workflow."""

import os
import logging
import json
import httpx
from schema.agent_state import AgentState

logger = logging.getLogger(__name__)

INTERNAL_API_URL = os.getenv("INTERNAL_API_URL", "http://api:8000")

_SEVERITY_MAP = {"none": 0, "early": 1, "middle": 2, "late": 3}

_SCORE_COLUMNS = (
    "neutral_score", "humor_sarcasm_score", "stress_score",
    "burnout_score", "depression_score", "harassment_score", "suicidal_ideation_score",
)


def _build_scores_payload(state: AgentState) -> dict:
    """Pass LLM scores (0-100 ints) through to incident_scores columns as 0.0-1.0 floats."""
    grades = (state.get("hr_report") or {}).get("scores") or {}

    def _norm(key: str) -> float:
        return round(min(1.0, max(0.0, float(grades.get(key, 0)) / 100.0)), 4)

    risk_scores = {
        col: _norm(col)
        for col in _SCORE_COLUMNS
        if col != "neutral_score" and col != "humor_sarcasm_score"
    }
    predicted_category = max(risk_scores, key=risk_scores.__getitem__)
    if risk_scores[predicted_category] < 0.2:
        predicted_category = "neutral"

    severity_str = str(state.get("filter_severity", "")).lower()

    return {
        col: _norm(col) for col in _SCORE_COLUMNS
    } | {
        "predicted_category": predicted_category,
        "predicted_severity": _SEVERITY_MAP.get(severity_str),
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
            if not response.is_success:
                logger.error(
                    f"[NODE: store_incident] API rejected incident — "
                    f"status={response.status_code} body={response.text!r} "
                    f"company_id={state['company_id']} user_id={payload['user_id']} "
                    f"source={payload['source']}"
                )
                return {**state, "store_succeeded": False, "store_error": response.text}
            response.raise_for_status()

        message_id = response.json().get("message_id")
        logger.info(f"[NODE: store_incident] Successfully stored incident {message_id}")

    except Exception as e:
        logger.error(f"[NODE: store_incident] Failed to store incident: {e}", exc_info=True)
        return {**state, "store_succeeded": False, "store_error": str(e)}

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
            logger.error(f"[NODE: store_incident] Failed to store scores for {message_id}: {e}", exc_info=True)

    return {**state, "store_succeeded": True, "store_error": None}
