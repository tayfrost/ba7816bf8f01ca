"""Risk assessment state node for the mental health assessment workflow."""

import logging
from langchain_core.messages import SystemMessage, HumanMessage
from schema.agent_state import AgentState
from utils.json_util import safe_json_loads
from llm import get_llm

logger = logging.getLogger(__name__)


async def assess_risk(state: AgentState) -> AgentState:
    """Assess if message indicates mental health risk."""
    from agent import prompt_service
    req = state.get("request_id", "n/a")
    
    llm = get_llm()
    
    logger.info(f"[NODE: assess_risk][req={req}] Starting risk assessment")
    logger.debug(f"[NODE: assess_risk] Input state keys: {list(state.keys())}")
    
    try:
        system_prompt = prompt_service.load_prompt(subfolder="assess_risk")
        logger.info(f"[NODE: assess_risk][req={req}] Prompt loaded successfully")
    except Exception as e:
        logger.error(f"[NODE: assess_risk][req={req}] Failed to load prompt: {e}")
        raise
    
    filter_category = state.get('filter_category') or 'unknown'
    filter_severity = state.get('filter_severity') or 'unknown'

    human_prompt = f"""Analyze this message for mental health risk: "{state['raw_message']}"

Upstream filter signal (treat as weak — see system prompt for how to weight this):
- filter_category: {filter_category}
- filter_severity: {filter_severity}

Respond with ONLY a JSON object:
{{"is_risk": true/false, "reasoning": "brief explanation"}}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    logger.info(f"[NODE: assess_risk][req={req}] Calling LLM for risk assessment")
    try:
        response = await llm.ainvoke(messages)
        content = response.content if response.content is not None else ""
        if isinstance(content, list):
            content = next((b["text"] for b in content if isinstance(b, dict) and "text" in b), "")
        logger.info(f"[NODE: assess_risk][req={req}] LLM response (first 100 chars): {content[:100]}")
        result = safe_json_loads(content)
        is_risk = bool(result.get('is_risk', False))
    except Exception as e:
        logger.exception(f"[NODE: assess_risk][req={req}] Assessment failed, defaulting to no risk: {e}")
        is_risk = False

    state['is_confirmed_risk'] = is_risk
    logger.info(f"[NODE: assess_risk][req={req}] Risk detected: {is_risk}")
    next_node = "grade_message" if is_risk else "END"
    logger.info(f"[NODE: assess_risk][req={req}] → Transition to {next_node}")
    return state
