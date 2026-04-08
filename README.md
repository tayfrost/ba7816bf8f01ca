# SentinelAI

SentinelAI is a multi-service platform for workplace wellbeing monitoring, risk triage, and operational analytics.

<https://github.kcl.ac.uk/k24000626/SentinelAI>

App: <https://sentinelai.work>

Model Link: <https://huggingface.co/OguzhanKOG/sentinelai-bert-filter>

Kishan Prakash – k23153494
Mariam Hafiz – k23115695
Dmytro Syzonenko – k24000626
Derja Sulevani – k24022340
Davyd Shtepa – k23109664
Lupupa Chansa – k23006355
Oguzhan Cagirir – k23175144
Daria Pampukha – k24057303
Vishal Thakwani - k24059655

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

## Monitoring (Grafana + Prometheus)

The full monitoring stack runs as part of `docker compose up` alongside the services.

**Dashboard URL:** `https://sentinelai.work/grafana/`

Anonymous users land in read-only **Viewer** mode — no login required. Admins log in with the credentials in `.env.grafana`.

### What is scraped

| Service | Endpoint | Key metrics |
|---|---|---|
| `api` | `api:8000/metrics` | HTTP latency, throughput, in-flight |
| `webhooks` | `webhooks:8000/metrics` | HTTP + Slack event processing |
| `payments` | `payments:8001/metrics` | HTTP latency, throughput |
| `ai_service` | `ai_service:8001/metrics` | HTTP + LangGraph pipeline latency/errors |
| `filter` | `filter:9091/metrics` | gRPC call latency, batch sizes, error rate |
| `postgres-exporter` | `postgres-exporter:9187` | DB size, active connections, incident counts |

### Useful PromQL queries

```promql
# Throughput per service (req/sec over last 5 min)
rate(http_requests_total[5m])

# p95 latency per endpoint
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# gRPC error rate for filter
rate(grpc_requests_total{outcome="error"}[5m])

# LangGraph agent p95 processing time
histogram_quantile(0.95, rate(ai_pipeline_duration_seconds_bucket[5m]))
```

---

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
