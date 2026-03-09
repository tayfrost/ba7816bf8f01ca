"""
SentinelAI Knowledge Graph MCP Server
Exposes the evidence-based mental health knowledge graph as MCP tools
for AI agents to query recommendations given a diagnosis.

Transport: SSE (Server-Sent Events) -- connect at http://<host>:<port>/sse

Modularized layout:
  sentinelai_kg/config.py      - env vars, constants, logging
  sentinelai_kg/data.py        - dataset resolution and loading
  sentinelai_kg/concerns.py    - topic keyword matching
  sentinelai_kg/formatting.py  - output helpers
  sentinelai_kg/tools.py       - FastMCP instance and all tool definitions
"""

from sentinelai_kg.config import MCP_HOST, MCP_PORT
from sentinelai_kg.data import get_dataset
from sentinelai_kg.tools import mcp

if __name__ == "__main__":
    get_dataset()
    mcp.run(transport="sse", host=MCP_HOST, port=MCP_PORT)
