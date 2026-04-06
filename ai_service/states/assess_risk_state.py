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
    
    llm = get_llm()
    
    logger.info("[NODE: assess_risk] Starting risk assessment")
    logger.debug(f"[NODE: assess_risk] Input state keys: {list(state.keys())}")
    
    try:
        system_prompt = prompt_service.load_prompt(subfolder="assess_risk")
        logger.info("[NODE: assess_risk] Prompt loaded successfully")
    except Exception as e:
        logger.error(f"[NODE: assess_risk] Failed to load prompt: {e}")
        raise
    
    human_prompt = f"""Analyze this message for mental health risk: "{state['raw_message']}"

Respond with ONLY a JSON object:
{{"is_risk": true/false, "reasoning": "brief explanation"}}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    logger.info("[NODE: assess_risk] Calling LLM for risk assessment")
    response = await llm.ainvoke(messages)
    logger.info(f"[NODE: assess_risk] LLM response (first 100 chars): {str(response.content)[:100]}")
    result = safe_json_loads(response.content)
    
    state['is_confirmed_risk'] = result['is_risk']
    logger.info(f"[NODE: assess_risk] Risk detected: {result['is_risk']}")
    logger.info(f"[NODE: assess_risk] Reasoning: {result.get('reasoning', 'N/A')}")
    
    next_node = "grade_message" if result['is_risk'] else "END"
    logger.info(f"[NODE: assess_risk] → Transition to {next_node}")
    return state
