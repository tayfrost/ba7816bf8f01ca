"""Message grading state node for the mental health assessment workflow."""

import logging
from langchain_core.messages import SystemMessage, HumanMessage
from schema.agent_state import AgentState
from utils.json_util import safe_json_loads
from llm import get_llm

logger = logging.getLogger(__name__)


async def grade_message(state: AgentState) -> AgentState:
    """Grade message across mental health dimensions."""
    from agent import prompt_service
    req = state.get("request_id", "n/a")
    
    llm = get_llm()
    
    logger.info(f"[NODE: grade_message][req={req}] Starting message grading")
    logger.debug(f"[NODE: grade_message] Input state keys: {list(state.keys())}")
    
    try:
        system_prompt = prompt_service.load_prompt(subfolder="grade_message")
        logger.info(f"[NODE: grade_message][req={req}] Prompt loaded successfully")
    except Exception as e:
        logger.error(f"[NODE: grade_message][req={req}] Failed to load prompt: {e}")
        raise
    
    filter_category = state.get('filter_category') or 'unknown'
    filter_severity = state.get('filter_severity') or 'unknown'

    human_prompt = f"""Score this message on mental health dimensions (0-100): "{state['raw_message']}"

Upstream filter signal (low-recall classifier — do not let it cap your scores, see system prompt):
- filter_category: {filter_category}
- filter_severity: {filter_severity}

Respond with ONLY a JSON object containing all of these fields with integer values between 0 and 100.
Missing any field or providing non-integer values will be treated as an error.
{{
  "neutral_score": 0-100,
  "humor_sarcasm_score": 0-100,
  "stress_score": 0-100,
  "burnout_score": 0-100,
  "depression_score": 0-100,
  "harassment_score": 0-100,
  "suicidal_ideation_score": 0-100
}}

Field guidance:
- neutral_score: how neutral / low-risk the message is overall (high = safe, low = concerning)
- humor_sarcasm_score: degree of humor or sarcasm present (does NOT reduce other scores)
- stress_score: occupational or situational stress indicators
- burnout_score: emotional exhaustion, detachment, reduced efficacy
- depression_score: low mood, hopelessness, anhedonia
- harassment_score: hostility, threats, bullying directed at or by the author
- suicidal_ideation_score: any self-harm or suicidal content"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]

    logger.info(f"[NODE: grade_message][req={req}] Calling LLM for scoring")
    default_scores = {
        "neutral_score": 100, "humor_sarcasm_score": 0, "stress_score": 0,
        "burnout_score": 0, "depression_score": 0, "harassment_score": 0,
        "suicidal_ideation_score": 0,
    }
    try:
        response = await llm.ainvoke(messages)
        content = response.content if response.content is not None else ""
        if isinstance(content, list):
            content = next((b["text"] for b in content if isinstance(b, dict) and "text" in b), "")
        logger.info(f"[NODE: grade_message][req={req}] LLM response (first 100 chars): {content[:100]}")
        scores = safe_json_loads(content)
        # Ensure all expected keys exist with safe defaults
        for k, v in default_scores.items():
            scores.setdefault(k, v)
        # Clamp all values to 0-100 int
        scores = {k: max(0, min(100, int(scores[k]))) for k in default_scores}
    except Exception as e:
        logger.exception(f"[NODE: grade_message][req={req}] Grading failed, using zero scores: {e}")
        scores = default_scores

    if state.get('hr_report') is None:
        state['hr_report'] = {}
    state['hr_report']['scores'] = scores

    logger.info(f"[NODE: grade_message][req={req}] Scores: {scores}")
    logger.info(f"[NODE: grade_message][req={req}] → Transition to generate_recommendations")
    return state
