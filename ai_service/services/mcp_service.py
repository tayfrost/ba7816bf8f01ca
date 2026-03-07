"""Service for connecting to and loading tools from MCP servers."""

import os
from typing import List
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from langchain_core.tools import StructuredTool


def mcp_to_tool(mcp_tool, client):
    """Convert MCP tool metadata to a StructuredTool with an async callable."""
    
    async def call_tool(**kwargs):
        # call the MCP server tool with provided args
        return await client.call_tool(mcp_tool.name, kwargs)

    return StructuredTool.from_function(
        name=mcp_tool.name,
        description=mcp_tool.description,
        args_schema=mcp_tool.inputSchema,
        coroutine=call_tool
    )


async def load_mcp_tools() -> list:
    """Load MCP tools and convert them to StructuredTool instances with callable."""
    kg_url = os.getenv("KG_MCP_URL")
    if not kg_url:
        return []
    
    async with Client(kg_url) as client:
        mcp_tools = await client.list_tools()
        return [mcp_to_tool(tool, client) for tool in mcp_tools]


async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Call a specific MCP tool with arguments."""
    kg_url = os.getenv("KG_MCP_URL")
    if not kg_url:
        raise ValueError("KG_MCP_URL not configured")
    
    async with Client(kg_url) as client:
        result = await client.call_tool(tool_name, arguments)
        return result.content[0].text if result.content else {}
