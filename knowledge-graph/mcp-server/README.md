# SentinelAI Knowledge Graph MCP Server

MCP server that exposes the SentinelAI evidence-based mental health knowledge graph as tools for AI agents.

**92 DOI-verified papers | 368 advice items | 24 topics | 37 techniques**

## Tools (10)

| Tool | Description |
|------|-------------|
| `triage_crisis_risk` | **Safety-critical** -- screen for self-harm/crisis before recommending |
| `get_recommendation` | **Primary** -- free-text diagnosis → ranked advice with DOI citations |
| `get_recommendation_by_topic` | Direct lookup by topic ID |
| `get_recommendation_by_technique` | Query by intervention method (CBT, mindfulness, etc.) |
| `list_topics` | List all 24 mental health topics |
| `list_techniques` | List all 37 evidence-based techniques |
| `get_techniques_for_topic` | Get techniques addressing a specific topic |
| `search_papers` | Search papers by keyword, topic, technique, or citations |
| `get_paper_details` | Full details of a specific paper with all advice |
| `get_stats` | Knowledge graph statistics |

## Safety Features

- **Crisis triage** -- `triage_crisis_risk` detects self-harm/suicide indicators and returns emergency resources
- **No silent fallback** -- returns explicit "no match" with guidance instead of guessing
- **Word-boundary matching** -- regex prevents false positives ("app" won't match "disappointed")
- **Input length bounding** -- 2000 char limit prevents DOS from oversized inputs
- **Medical disclaimer** -- included in all recommendation responses and enforced via system instructions

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

## Agent Usage Priority

1. **`triage_crisis_risk`** -- ALWAYS call first if user mentions self-harm or severe distress
2. **`get_recommendation`** -- primary tool for any user concern (auto-detects topics)
3. **`get_recommendation_by_topic`** -- when you know the exact topic
4. **`get_recommendation_by_technique`** -- when recommending a specific intervention
5. **`list_topics` / `list_techniques`** -- for discovery and browsing
6. **`search_papers`** -- for research-specific queries
