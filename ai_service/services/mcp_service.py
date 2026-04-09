"""Service for connecting to and loading tools from MCP servers."""

import os
from typing import List, AsyncGenerator
import logging
from fastmcp import Client
from langchain_core.tools import StructuredTool


logger = logging.getLogger(__name__)


async def get_mcp_client() -> AsyncGenerator[Client, None]:
    """Factory function to create a new MCP client instance per request."""
    kg_url = os.getenv("KG_MCP_URL")
    if not kg_url:
        raise ValueError("KG_MCP_URL not configured")

    logger.info("[MCP] Opening client connection to %s", kg_url)
    try:
        async with Client(kg_url) as client:
            logger.info("[MCP] Client connected to %s", kg_url)
            yield client
    except Exception:
        logger.exception("[MCP] Client connection/use failed for %s", kg_url)
        raise
    finally:
        logger.info("[MCP] Client connection closed for %s", kg_url)


def mcp_to_tool(mcp_tool, client: Client):
    """Convert MCP tool metadata to a StructuredTool with an async callable."""

    async def call_tool(**kwargs):
        logger.info(
            "[MCP] Calling tool=%s args_keys=%s",
            mcp_tool.name,
            sorted(list(kwargs.keys())),
        )
        try:
            result = await client.call_tool(mcp_tool.name, kwargs)
            result_preview = str(result)
            if len(result_preview) > 240:
                result_preview = f"{result_preview[:240]}..."
            logger.info("[MCP] Tool=%s completed result_preview=%s", mcp_tool.name, result_preview)
            return result
        except Exception:
            logger.exception("[MCP] Tool=%s failed", mcp_tool.name)
            raise

    return StructuredTool.from_function(
        name=mcp_tool.name,
        description=mcp_tool.description,
        args_schema=mcp_tool.inputSchema,
        coroutine=call_tool,
    )


async def load_mcp_tools(client: Client) -> list:
    """Load MCP tools and convert them to StructuredTool instances."""
    logger.info("[MCP] Loading tool catalog")
    try:
        mcp_tools = await client.list_tools()
        logger.info("[MCP] Loaded %s tools: %s", len(mcp_tools), [t.name for t in mcp_tools])
        return [mcp_to_tool(tool, client) for tool in mcp_tools]
    except Exception:
        logger.exception("[MCP] Failed to load tool catalog")
        raise


async def call_mcp_tool(client: Client, tool_name: str, arguments: dict) -> dict:
    """Call a specific MCP tool with arguments."""
    logger.info("[MCP] Direct call tool=%s args_keys=%s", tool_name, sorted(list(arguments.keys())))
    try:
        result = await client.call_tool(tool_name, arguments)
        return result.content[0].text if result.content else {}
    except Exception:
        logger.exception("[MCP] Direct call tool=%s failed", tool_name)
        raise