# SentinelAI

SentinelAI is a multi-service platform for workplace wellbeing monitoring, risk triage, and operational analytics.

## Core Services

- **API** (`api/`) — auth, company/user management, integrations, incidents, metrics.
- **Webhooks** (`webhooks/`) — Slack/Gmail intake and filter dispatch.
- **Filter** (`filter/`) — gRPC classifier (PyTorch-first, optional ONNX).
- **AI Service** (`ai_service/`) — LangGraph-based deeper assessment and recommendations.
- **Payments** (`payments/`) — Stripe-backed subscription and billing workflows.
- **Knowledge Graph MCP** (`knowledge-graph/mcp-server/`) — evidence-backed recommendation tools for agents.
- **Database Layer** (`database/`) — schema bootstrap and CRUD/table tests.
- **Frontend** (`frontend/`) — React + TypeScript + Vite UI.

## Repository Layout

```text
SentinelAI/
├── ai_service/
├── api/
├── database/
├── datasets/
├── filter/
├── frontend/
├── knowledge-graph/
├── payments/
├── testing/
├── webhooks/
└── docker-compose.yaml
```

## Quick Start (Docker Compose)

From repository root:

```bash
docker compose up -d
```

Common targeted startup:

```bash
docker compose up -d pgvector api webhooks filter ai_service payments kg-mcp-server
```

## CI Summary

Workflow file: `.github/workflows/ci.yml`

Current jobs are split into:

- **Blocking/stable gates**
  - Frontend lint + build
  - Filter tests
  - Payments smoke tests
  - Database table tests
- **Advisory jobs** (non-blocking while integration settles)
  - AI service tests
  - Knowledge graph tests
  - Webhooks unit tests
  - API tests

## Testing Entry Points

- API tests: `run_api_tests.ps1`
- Webhooks tests: `run_webhook_tests.ps1`
- Filter tests: `pytest -q filter/tests`
- Resilience/load suite: `testing/`

## Documentation Index

- [API guide](api/README.md)
- [Webhooks guide](webhooks/README.md)
- [Filter inference guide](filter/inference/README.md)
- [AI service guide](ai_service/README.md)
- [Payments guide](payments/README.md)
- [Knowledge graph guide](knowledge-graph/README.md)
- [Knowledge graph MCP server guide](knowledge-graph/mcp-server/README.md)
- [Database schema guide](database/README.md)
- [Datasets guide](datasets/README.md)
- [Testing guide](testing/README.md)
- [Frontend guide](frontend/README.md)
