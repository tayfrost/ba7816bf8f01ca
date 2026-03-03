"""Service for connecting to and loading tools from MCP servers."""

import os
from typing import List
from mcp import ClientSession
from mcp.client.sse import sse_client


async def load_mcp_tools(session: ClientSession) -> List:
    """Load tools from an MCP session."""
    result = await session.list_tools()
    return result.tools


async def load_all_tools() -> List:
    """Load tools from all configured MCP servers."""
    tools = []
    
    # Load from Knowledge Graph MCP server
    kg_url = os.getenv("KG_MCP_URL")
    if kg_url:
        async with sse_client(kg_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools += await load_mcp_tools(session)
    
    # Load from additional MCP server if configured
    another_url = os.getenv("ANOTHER_MCP_URL")
    if another_url:
        async with sse_client(another_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools += await load_mcp_tools(session)
    
    return tools


async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Call a specific MCP tool with arguments."""
    kg_url = os.getenv("KG_MCP_URL")
    if not kg_url:
        raise ValueError("KG_MCP_URL not configured")
    
    async with sse_client(kg_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result.content[0].text if result.content else {}
