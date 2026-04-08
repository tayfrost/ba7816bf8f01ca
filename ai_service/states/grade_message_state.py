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
    
    llm = get_llm()
    
    logger.info("[NODE: grade_message] Starting message grading")
    logger.debug(f"[NODE: grade_message] Input state keys: {list(state.keys())}")
    
    try:
        system_prompt = prompt_service.load_prompt(subfolder="grade_message")
        logger.info("[NODE: grade_message] Prompt loaded successfully")
    except Exception as e:
        logger.error(f"[NODE: grade_message] Failed to load prompt: {e}")
        raise
    
    human_prompt = f"""Score this message on mental health dimensions (0-100): "{state['raw_message']}"

Respond with ONLY a JSON object, which has to obtain all of these fields with integer values between 0 and 100, missing any field or providing non-integer values will be considered an error:
{{
  "stress_level": 0-100,
  "suicide_risk": 0-100,
  "burnout_score": 0-100,
  "depression_indicators": 0-100,
  "harassment_score": 0-100,
  "isolation_tendency": 0-100
}}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    logger.info("[NODE: grade_message] Calling LLM for scoring")
    default_scores = {
        "stress_level": 0, "suicide_risk": 0, "burnout_score": 0,
        "depression_indicators": 0, "harassment_score": 0, "isolation_tendency": 0,
    }
    try:
        response = await llm.ainvoke(messages)
        content = response.content if response.content is not None else ""
        if isinstance(content, list):
            content = next((b["text"] for b in content if isinstance(b, dict) and "text" in b), "")
        logger.info(f"[NODE: grade_message] LLM response (first 100 chars): {content[:100]}")
        scores = safe_json_loads(content)
        # Ensure all expected keys exist
        for k, v in default_scores.items():
            scores.setdefault(k, v)
    except Exception as e:
        logger.warning(f"[NODE: grade_message] Grading failed, using zero scores: {e}")
        scores = default_scores

    if state.get('hr_report') is None:
        state['hr_report'] = {}
    state['hr_report']['scores'] = scores

    logger.info(f"[NODE: grade_message] Scores: {scores}")
    logger.info("[NODE: grade_message] → Transition to generate_recommendations")
    return state
