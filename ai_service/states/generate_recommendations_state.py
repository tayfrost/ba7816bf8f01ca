"""Recommendations generation state node for the mental health assessment workflow."""

import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from schema.agent_state import AgentState
from services.mcp_service import load_mcp_tools
from utils.json_util import safe_json_loads
from llm import get_llm_for_tools


logger = logging.getLogger(__name__)


def _format_tools_catalog(tools: list) -> str:
    """
    Build a human-readable catalog of available MCP tools to inject into the system prompt.
    Lists exact names (the only valid values the LLM may call) plus descriptions and parameters.
    """
    if not tools:
        return "  (no tools available — proceed directly to report synthesis without any tool calls)"

    parts = []
    for i, tool in enumerate(tools, 1):
        name = getattr(tool, "name", str(tool))
        desc = (getattr(tool, "description", "") or "No description available").strip()

        # Try to extract parameter schema from the StructuredTool's args_schema
        param_lines: list[str] = []
        args_schema = getattr(tool, "args_schema", None)
        if args_schema is not None:
            try:
                if hasattr(args_schema, "model_json_schema"):
                    schema_dict = args_schema.model_json_schema()
                elif hasattr(args_schema, "schema"):
                    schema_dict = args_schema.schema()
                else:
                    schema_dict = {}

                props = schema_dict.get("properties", {})
                required = set(schema_dict.get("required", []))

                for param, info in props.items():
                    req_label = "required" if param in required else "optional"
                    p_type = info.get("type", "string")
                    p_desc = info.get("description", "")
                    suffix = f" — {p_desc}" if p_desc else ""
                    param_lines.append(f"        • {param} ({p_type}, {req_label}){suffix}")
            except Exception as exc:
                logger.debug(f"[tools_catalog] Could not extract schema for {name!r}: {exc}")

        params_block = (
            "\n" + "\n".join(param_lines)
            if param_lines
            else " (none)"
        )

        parts.append(
            f"  [{i}] Tool name (use exactly): {name!r}\n"
            f"      What it does: {desc}\n"
            f"      Parameters:{params_block}"
        )

    return "\n\n".join(parts)


async def generate_recommendations(state: AgentState, config: RunnableConfig) -> AgentState:
    """Generate HR recommendations based on assessment with evidence-based advice from knowledge graph."""
    from agent import prompt_service
    
    llm = get_llm_for_tools()
    
    logger.info("[NODE: generate_recommendations] Starting recommendations generation")
    logger.debug(f"[NODE: generate_recommendations] Input state keys: {list(state.keys())}")
    
    scores = state['hr_report']['scores']
    raw_message = state['raw_message']
    filter_category = state.get('filter_category', 'unknown')
    filter_severity = state.get('filter_severity', 'unknown')

    # Load MCP tools FIRST so we can inject the live catalog into the system prompt
    logger.info("[NODE: generate_recommendations] Loading MCP tools")
    mcp_client = config.get("configurable", {}).get("mcp_client")
    kg_tools = await load_mcp_tools(mcp_client)
    logger.info(f"[NODE: generate_recommendations] Loaded {len(kg_tools)} MCP tools: {[t.name for t in kg_tools]}")

    try:
        system_prompt_template = prompt_service.load_prompt(subfolder="generate_recommendations")
        logger.info("[NODE: generate_recommendations] Prompt template loaded successfully")
    except Exception as e:
        logger.error(f"[NODE: generate_recommendations] Failed to load prompt: {e}")
        raise

    # Inject the live tool catalog so the model knows exactly which names are valid
    tools_catalog = _format_tools_catalog(kg_tools)
    system_prompt = system_prompt_template.replace("{tools_catalog}", tools_catalog)

    llm_with_tools = llm.bind_tools(kg_tools) if kg_tools else llm

    human_prompt = f"""<case>
<message>{raw_message}</message>
<scores>
{json.dumps(scores, indent=2)}
</scores>
<detection_category>{filter_category}</detection_category>
<detection_severity>{filter_severity}</detection_severity>
</case>

Follow the reasoning protocol in the system prompt. Call relevant tools if applicable, then output the JSON report and nothing else."""

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

        # Store in state — use .get() in case the LLM omits a key
        state["hr_report"]["recommendations"] = result.get("recommendations", [])
        state["hr_report"]["response"] = result.get("response", result.get("reasoning", ""))

        logger.info("[NODE: generate_recommendations] → Transition to END")
        return state

    raise RuntimeError("LLM did not produce final response after tool calls")
