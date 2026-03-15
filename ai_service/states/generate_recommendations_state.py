"""Recommendations generation state node for the mental health assessment workflow."""

import os
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from schema.agent_state import AgentState
from services.mcp_service import load_mcp_tools
from utils.json_util import safe_json_loads


logger = logging.getLogger(__name__)


async def generate_recommendations(state: AgentState) -> AgentState:
    """Generate HR recommendations based on assessment with evidence-based advice from knowledge graph."""
    from agent import prompt_service
    
    llm = ChatOpenAI(
        model=os.getenv("MODEL", "gpt-5-nano"),
        api_key=os.getenv("OPENAI_API_KEY"),
        use_responses_api=True,
        temperature=1
    )
    
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
    kg_tools = await load_mcp_tools(state['mcp_client'])
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
    
    # Tool-calling loop: iterate until final text response
    max_iterations = 5
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        logger.info(f"[NODE: generate_recommendations] Iteration {iteration}/{max_iterations}")

        response = await llm_with_tools.ainvoke(messages)

        # If the model wants to call tools
        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(f"[NODE: generate_recommendations] Tool calls detected: {response.tool_calls}")

            # Append the assistant message that requested the tools
            messages.append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]

                logger.info(f"[NODE: generate_recommendations] Executing tool: {tool_name} with args: {tool_args}")

                try:
                    tool = next(t for t in kg_tools if t.name == tool_name)
                except StopIteration:
                    raise RuntimeError(f"Tool {tool_name} not found among loaded MCP tools")

                # Execute tool
                tool_result = await tool.ainvoke(tool_args)

                logger.info(f"[NODE: generate_recommendations] Tool result received")

                # Append tool result properly
                messages.append(
                    ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call_id
                    )
                )

            continue

        # -------------------------
        # Final response extraction
        # -------------------------

        if hasattr(response, "content"):
            content_text = response.content
        else:
            content_text = str(response)

        # Responses API sometimes returns list blocks
        if isinstance(content_text, list):
            for item in content_text:
                if isinstance(item, dict) and "text" in item:
                    content_text = item["text"]
                    break
            else:
                content_text = str(content_text[0])

        if content_text and isinstance(content_text, str) and content_text.strip():
            logger.info(f"[NODE: generate_recommendations] Final response (first 100 chars): {content_text[:100]}")

            try:
                result = safe_json_loads(content_text)
            except json.JSONDecodeError as e:
                logger.error(f"[NODE: generate_recommendations] JSON decode failed: {e}")
                raise RuntimeError("Failed to parse JSON from LLM response")
        else:
            raise RuntimeError("LLM did not produce valid text response")

        # Ensure hr_report exists
        if "hr_report" not in state or state["hr_report"] is None:
            state["hr_report"] = {}

        # Store in state
        state["hr_report"]["recommendations"] = result["recommendations"]
        state["hr_report"]["response"] = result["response"]

        logger.info("[NODE: generate_recommendations] → Transition to END")
        return state

    raise RuntimeError("LLM did not produce final response after tool calls")
