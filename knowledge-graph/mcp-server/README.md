# SentinelAI Knowledge Graph MCP Server

MCP server that exposes the SentinelAI evidence-based mental health knowledge graph as tools for AI agents.

**92 DOI-verified papers | 368 advice items | 24 topics | 37 techniques**

## Tools

| Tool | Description |
|------|-------------|
| `get_recommendation` | Get ranked advice for a diagnosis/concern (free-text input) |
| `get_recommendation_by_topic` | Get advice for a specific topic ID |
| `list_topics` | List all 24 mental health topics |
| `get_techniques_for_topic` | Get techniques addressing a specific topic |
| `search_papers` | Search papers by keyword, topic, or technique |
| `get_paper_details` | Full details of a specific paper with all advice |
| `list_techniques` | List all 37 evidence-based techniques |
| `get_stats` | Knowledge graph statistics |

## Setup

### With uv (recommended)

```bash
cd knowledge-graph/mcp-server
uv run server.py
```

### With pip

```bash
cd knowledge-graph/mcp-server
pip install "mcp[cli]"
python server.py
```

## Connecting to an AI Agent

### Claude Desktop / Cursor

Add to your MCP config:

```json
{
  "sentinelai-kg": {
    "command": "uv",
    "args": ["run", "--directory", "/path/to/SentinelAI/knowledge-graph/mcp-server", "server.py"]
  }
}
```

### Programmatic (stdio)

```bash
uv run server.py
```

The server communicates over stdio using the MCP protocol.

## Example Usage

An AI agent connected to this MCP server can:

1. **Triage a diagnosis** → Call `get_recommendation("patient reports burnout, insomnia, and anxiety")`
2. **Explore a topic** → Call `list_topics()` then `get_recommendation_by_topic("burnout")`
3. **Find evidence** → Call `search_papers(query="CBT", min_citations=100)`
4. **Drill into a paper** → Call `get_paper_details("paper_001")`

All responses include DOI citations, confidence scores, and technique names.
