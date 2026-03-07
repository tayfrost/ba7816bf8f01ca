"""Redactor state node for the mental health assessment workflow."""

import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from schema.agent_state import AgentState

logger = logging.getLogger(__name__)


async def redactor(state: AgentState) -> AgentState:
    """Redact company-sensitive information while preserving employee mental health indicators."""
    from agent import llm, prompt_service
    
    logger.info("[NODE: redactor] Starting redaction")
    logger.debug(f"[NODE: redactor] Input state keys: {list(state.keys())}")
    
    try:
        system_prompt = prompt_service.load_prompt(subfolder="redactor")
        logger.info("[NODE: redactor] Prompt loaded successfully")
    except Exception as e:
        logger.error(f"[NODE: redactor] Failed to load redactor prompt: {e}")
        raise
    
    human_prompt = f"""Original message: "{state['raw_message']}"

Respond with ONLY a JSON object:
{{"redacted_message": "message with company info redacted"}}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    logger.info("[NODE: redactor] Calling LLM for redaction")
    response = await llm.ainvoke(messages)
    result = json.loads(response.content)
    logger.info(f"[NODE: redactor] Redaction complete")
    
    state['raw_message'] = result['redacted_message']
    logger.info("[NODE: redactor] → Transition to assess_risk")
    return state
