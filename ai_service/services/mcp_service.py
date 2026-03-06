"""Service for connecting to and loading tools from MCP servers."""

import os
from typing import List
from fastmcp import Client


async def load_mcp_tools() -> List:
    """Load tools from KG MCP server via Streamable HTTP."""
    kg_url = os.getenv("KG_MCP_URL")
    if not kg_url:
        return []
    
    async with Client(kg_url) as client:
        result = await client.list_tools()
        return result.tools


async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Call a specific MCP tool with arguments."""
    kg_url = os.getenv("KG_MCP_URL")
    if not kg_url:
        raise ValueError("KG_MCP_URL not configured")
    
    async with Client(kg_url) as client:
        result = await client.call_tool(tool_name, arguments)
        return result.content[0].text if result.content else {}
