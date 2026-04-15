# SentinelAI Knowledge Graph MCP Server

MCP server that exposes the SentinelAI evidence-based mental health knowledge graph as tools for AI agents via **streamable-http** transport.

**92 DOI-verified papers | 368 advice items | 24 topics | 37 techniques**

## Architecture

```
┌──────────────┐  streamable-http    ┌──────────────────┐
│   AI Agent   │ ──────────────────▶ │  KG MCP Server   │
│  (Dima's     │ ◀────────────────── │  :8001/mcp       │
│   system)    │   tool responses    │                  │
└──────────────┘                     └───────┬──────────┘
                                             │
                                     ┌───────▼──────────┐
                                     │  papers.json     │
                                     │  (local or HF)   │
                                     └──────────────────┘
```

## Deployment (Docker — recommended)

The MCP server runs as part of the global `docker-compose.yaml` at the repo root.

```bash
# From repo root — start all services including the MCP server
docker compose up -d

# Start only the MCP server
docker compose up -d kg-mcp-server

# View logs
docker compose logs -f kg-mcp-server
```

Once running, the MCP server is available at:

| Endpoint | URL | Description |
|----------|-----|-------------|
| MCP endpoint | `http://localhost:8001/mcp` | AI agent connects here |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HOST` | `0.0.0.0` | Host to bind the MCP server |
| `MCP_PORT` | `8001` | Port for the MCP server |
| `KG_DATA_PATH` | `./data/papers.json` | Local path to dataset (fallback) |
| `HF_DATASET_REPO` | *(empty)* | HuggingFace dataset repo ID (e.g. `SentinelAI/kg-data`). If set, downloads dataset from HF on startup |
| `HF_DATASET_FILE` | `papers.json` | Filename within the HF dataset repo |

### Port Reference

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| KG MCP Server | 8001 | HTTP | AI agent MCP tool calls |
| Neo4j Browser | 7474 | HTTP | Graph visualization (dev only) |
| Neo4j Bolt | 7687 | Bolt | Graph database protocol (dev only) |

> **Note:** Neo4j is behind the `dev` profile — it only starts when you run `docker compose --profile dev up`. The MCP server does **not** require Neo4j; it reads directly from the JSON dataset.

## Local Development (without Docker)

```bash
cd knowledge-graph/mcp-server
pip install -r requirements.txt
python server.py
```

The server starts on `http://0.0.0.0:8001/mcp` with streamable-http transport.

## Connecting an AI Agent to this MCP Server

Point your MCP client at:

```
http://localhost:8001/mcp
```

Example MCP client config:

```json
{
  "sentinelai-kg": {
    "transport": "streamable-http",
    "url": "http://localhost:8001/mcp"
  }
}
```

### From another Docker container on the same network

```
http://kg-mcp-server:8001/mcp
```

The service name `kg-mcp-server` resolves within the Docker Compose network.

## Dataset Source

The knowledge graph dataset (`papers.json`) can be loaded from:

1. **HuggingFace Hub** (production) — set `HF_DATASET_REPO` env var
2. **Local file** (fallback) — baked into the Docker image at `/app/data/papers.json`

To switch to HuggingFace loading:

```yaml
# In docker-compose.yaml, add to kg-mcp-server environment:
- HF_DATASET_REPO=SentinelAI/kg-data
```

## Tools (11)

| Tool | Description |
|------|-------------|
| `triage_crisis_risk` | **Safety-critical** — screen for self-harm/crisis before recommending |
| `get_recommendation` | **Primary** — free-text diagnosis → ranked advice with DOI citations |
| `get_recommendation_by_topic` | Direct lookup by topic ID |
| `get_recommendation_by_technique` | Query by intervention method (CBT, mindfulness, etc.) |
| `list_topics` | List all 24 mental health topics |
| `list_techniques` | List all 37 evidence-based techniques |
| `get_techniques_for_topic` | Get techniques addressing a specific topic |
| `search_papers` | Search papers by keyword, topic, technique, or citations |
| `get_paper_details` | Full details of a specific paper with all advice |
| `get_stats` | Knowledge graph statistics |

## Safety Features

- **Crisis triage** — `triage_crisis_risk` detects self-harm/suicide indicators and returns UK emergency resources (Samaritans, NHS 111, Crisis Text Line)
- **No silent fallback** — returns explicit "no match" with guidance instead of guessing
- **Word-boundary matching** — regex prevents false positives
- **Input length bounding** — 2000 char limit prevents abuse
- **Medical disclaimer** — included in all recommendation responses

## Agent Usage Priority

1. **`triage_crisis_risk`** — ALWAYS call first if user mentions self-harm or severe distress
2. **`get_recommendation`** — primary tool for any user concern (auto-detects topics)
3. **`get_recommendation_by_topic`** — when you know the exact topic
4. **`get_recommendation_by_technique`** — when recommending a specific intervention
5. **`list_topics` / `list_techniques`** — for discovery and browsing
6. **`search_papers`** — for research-specific queries
