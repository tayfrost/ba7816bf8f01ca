"""Service for connecting to and loading tools from MCP servers."""

import os
from typing import List
from fastmcp import Client
from langchain_core.tools import StructuredTool

# --- Internal MCP client singleton ---
_client: Client | None = None


async def _get_client() -> Client:
    """Return a persistent MCP client instance."""
    global _client

    if _client is None:
        kg_url = os.getenv("KG_MCP_URL")
        if not kg_url:
            raise ValueError("KG_MCP_URL not configured")

        _client = Client(kg_url)
        await _client.__aenter__()  # manually enter async context

    return _client


def mcp_to_tool(mcp_tool, client: Client):
    """Convert MCP tool metadata to a StructuredTool with an async callable."""

    async def call_tool(**kwargs):
        return await client.call_tool(mcp_tool.name, kwargs)

    return StructuredTool.from_function(
        name=mcp_tool.name,
        description=mcp_tool.description,
        args_schema=mcp_tool.inputSchema,
        coroutine=call_tool,
    )


async def load_mcp_tools() -> list:
    """Load MCP tools and convert them to StructuredTool instances."""
    client = await _get_client()

    mcp_tools = await client.list_tools()
    return [mcp_to_tool(tool, client) for tool in mcp_tools]


async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Call a specific MCP tool with arguments."""
    client = await _get_client()

    result = await client.call_tool(tool_name, arguments)
    return result.content[0].text if result.content else {}