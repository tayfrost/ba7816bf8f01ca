"""Redactor state node for the mental health assessment workflow."""

import logging
from langchain_core.messages import SystemMessage, HumanMessage
from schema.agent_state import AgentState
from utils.json_util import safe_json_loads
from llm import get_llm

logger = logging.getLogger(__name__)


async def redactor(state: AgentState) -> AgentState:
    """Redact company-sensitive information while preserving employee mental health indicators."""
    from agent import prompt_service
    
    llm = get_llm()
    
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
    try:
        response = await llm.ainvoke(messages)
        content = response.content if response.content is not None else ""
        if isinstance(content, list):
            content = next((b["text"] for b in content if isinstance(b, dict) and "text" in b), "")
        logger.info(f"[NODE: redactor] LLM response (first 100 chars): {content[:100]}")
        result = safe_json_loads(content)
        state['raw_message'] = result.get('redacted_message') or state['raw_message']
        logger.info(f"[NODE: redactor] Redaction complete")
    except Exception as e:
        logger.warning(f"[NODE: redactor] Redaction failed, using original message: {e}")
    logger.info("[NODE: redactor] → Transition to assess_risk")
    return state
