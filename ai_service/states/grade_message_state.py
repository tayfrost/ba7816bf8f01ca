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
    response = await llm.ainvoke(messages)
    logger.info(f"[NODE: grade_message] LLM response (first 100 chars): {str(response.content)[:100]}")
    scores = safe_json_loads(response.content)
    
    # Store scores in state for recommendations node
    if state.get('hr_report') is None:
        state['hr_report'] = {}
    state['hr_report']['scores'] = scores
    
    logger.info(f"[NODE: grade_message] Scores: {scores}")
    logger.info("[NODE: grade_message] → Transition to generate_recommendations")
    return state
