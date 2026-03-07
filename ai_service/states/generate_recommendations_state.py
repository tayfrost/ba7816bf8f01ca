"""Recommendations generation state node for the mental health assessment workflow."""

import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from schema.agent_state import AgentState
from services.mcp_service import load_mcp_tools

logger = logging.getLogger(__name__)


async def generate_recommendations(state: AgentState) -> AgentState:
    """Generate HR recommendations based on assessment with evidence-based advice from knowledge graph."""
    from agent import llm, prompt_service
    
    logger.info("[NODE: generate_recommendations] Starting recommendations generation")
    logger.debug(f"[NODE: generate_recommendations] Input state keys: {list(state.keys())}")
    
    try:
        system_prompt = prompt_service.load_prompt(subfolder="generate_recommendations")
        logger.info("[NODE: generate_recommendations] Prompt loaded successfully")
    except Exception as e:
        logger.error(f"[NODE: generate_recommendations] Failed to load prompt: {e}")
        raise
    
    scores = state['hr_report']['scores']
    raw_message = state['raw_message']
    
    # Load and bind MCP tools
    logger.info("[NODE: generate_recommendations] Loading MCP tools")
    kg_tools = await load_mcp_tools()
    logger.info(f"[NODE: generate_recommendations] Loaded {len(kg_tools)} MCP tools")
    
    llm_with_tools = llm.bind_tools(kg_tools) if kg_tools else llm
    
    human_prompt = f"""Based on message: "{raw_message}"
And scores: {json.dumps(scores)}

Use available MCP tools to gather evidence-based recommendations.
If crisis detected, prioritize crisis resources.
Generate HR recommendations and detailed analysis response.
Respond with JSON:
{{"recommendations": ["rec1", "rec2"], "response": "detailed analysis text"}}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    logger.info("[NODE: generate_recommendations] Calling LLM with bound MCP tools")
    response = await llm_with_tools.ainvoke(messages)
    result = json.loads(response.content)
    
    state['hr_report']['recommendations'] = result['recommendations']
    state['hr_report']['response'] = result['response']
    
    logger.info(f"[NODE: generate_recommendations] Generated {len(result['recommendations'])} recommendations")
    logger.info("[NODE: generate_recommendations] → Transition to END")
    return state
