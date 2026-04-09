# SentinelAI

**Team 7** | Large Group Project | King's College London — BSc Artificial Intelligence

SentinelAI is a multi-service platform for workplace wellbeing monitoring, automated risk triage, and operational analytics. It ingests communication signals from Slack and Gmail, classifies them through a fine-tuned BERT model, escalates high-risk incidents via an LLM-powered assessment pipeline, and surfaces actionable insights to managers through a React dashboard.

---

## Team Members

| Name | Student ID |
|---|---|
| Kishan Prakash | k23153494 |
| Mariam Hafiz | k23115695 |
| Dmytro Syzonenko | k24000626 |
| Derja Sulevani | k24022340 |
| Davyd Shtepa | k23109664 |
| Lupupa Chansa | k23006355 |
| Oguzhan Cagirir | k23175144 |
| Daria Pampukha | k24057303 |
| Vishal Thakwani | k24059655 |

---

## Links

- **Git repository:** https://github.kcl.ac.uk/k24000626/SentinelAI
- **Deployed application:** https://sentinelai.work
- **Trained model (Hugging Face):** https://huggingface.co/OguzhanKOG/sentinelai-bert-filter
- **Monitoring dashboard (Grafana):** https://sentinelai.work/grafana/ *(anonymous read-only access)*

---

## Architecture Overview

SentinelAI is decomposed into seven independently deployable services orchestrated via Docker Compose. All inter-service communication is either REST/HTTP or gRPC.

```
SentinelAI/
├── ai_service/          # LangGraph-based deep assessment + recommendations
├── api/                 # Core REST API: auth, companies, users, incidents, metrics
├── database/            # Schema bootstrap and CRUD/table tests
├── datasets/            # Training and evaluation data for the filter model
├── filter/              # gRPC classifier service (BERT fine-tune, optional ONNX)
├── frontend/            # React + TypeScript + Vite dashboard
├── knowledge-graph/     # Evidence-backed recommendation tools + MCP server
├── payments/            # Stripe-backed subscription and billing workflows
├── testing/             # Resilience and load test suite
├── webhooks/            # Slack/Gmail intake and filter dispatch
└── docker-compose.yaml
```

### Service Responsibilities

**API** (`api/`) handles all authentication (JWT), company and user management, integration configuration, incident CRUD, and the metrics aggregation layer. It exposes a Prometheus `/metrics` endpoint.

**Webhooks** (`webhooks/`) receives inbound events from Slack Event API and Gmail push notifications. It normalises payloads, invokes the filter service via gRPC, and forwards classified high-risk signals to the API for incident creation.

**Filter** (`filter/`) runs a fine-tuned BERT classifier over a gRPC interface. The model is served in PyTorch-native mode by default; ONNX export is supported for latency-sensitive deployments. The model was trained on a labelled workplace communication dataset and is published at the Hugging Face link above.

**AI Service** (`ai_service/`) runs a LangGraph agentic pipeline that receives escalated incidents, performs multi-step contextual assessment, and produces structured recommendations. It integrates with the knowledge graph MCP server for evidence retrieval.

**Payments** (`payments/`) wraps Stripe's API for subscription creation, cancellation, webhook handling, and metered billing.

**Knowledge Graph MCP Server** (`knowledge-graph/mcp-server/`) exposes MCP-compatible tools over HTTP that the AI service agent calls during reasoning. The graph encodes domain evidence linking communication patterns to wellbeing risk factors.

**Frontend** (`frontend/`) is a React + TypeScript + Vite single-page application. It communicates with the API service and renders the incident dashboard, analytics views, and company/user management screens.

---

## Prerequisites

- Docker >= 24 and Docker Compose >= 2.20
- Git
- Ports 80, 443, 5432, 8000, 8001, 9090, 9091, 3000 free on the host (or override via `.env`)

No local Python, Node, or database installations are required — everything runs inside containers.

---

## Setup and Installation

### 1. Clone the repository

```bash
git clone https://github.kcl.ac.uk/k24000626/SentinelAI.git
cd SentinelAI
```

### 2. Environment files

All `.env` files ship with working example values at their example paths. Copy each one into place:

```bash
# Root-level compose env
cp .env.example .env

# Per-service envs
cp api/.env.example             api/.env
cp webhooks/.env.example        webhooks/.env
cp filter/.env.example          filter/.env
cp ai_service/.env.example      ai_service/.env
cp payments/.env.example        payments/.env
cp knowledge-graph/.env.example knowledge-graph/.env
cp frontend/.env.example        frontend/.env

# Monitoring
cp .env.grafana.example         .env.grafana
cp .env.prometheus.example      .env.prometheus
```

The example values are sufficient to boot the full stack locally. For a production deployment, replace the following before starting:

| Variable | Where | What to set |
|---|---|---|
| `SECRET_KEY` | `api/.env` | A long random string (e.g. `openssl rand -hex 32`) |
| `STRIPE_SECRET_KEY` | `payments/.env` | Your Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | `payments/.env` | Stripe webhook signing secret |
| `OPENAI_API_KEY` | `ai_service/.env` | OpenAI API key for the LangGraph agent |
| `SLACK_BOT_TOKEN` | `webhooks/.env` | Slack bot OAuth token |
| `SLACK_SIGNING_SECRET` | `webhooks/.env` | Slack app signing secret |
| `GMAIL_CREDENTIALS` | `webhooks/.env` | Path to Google service account JSON |
| `GF_SECURITY_ADMIN_PASSWORD` | `.env.grafana` | Grafana admin password |
| `POSTGRES_PASSWORD` | `.env` | Postgres superuser password |

### 3. Start the full stack

```bash
docker compose up -d
```

This brings up: `pgvector`, `api`, `webhooks`, `filter`, `ai_service`, `payments`, `kg-mcp-server`, `frontend`, `prometheus`, `grafana`, and `postgres-exporter`.

Wait for all services to report healthy:

```bash
docker compose ps
```

The frontend is served at `http://localhost` (port 80). The API is at `http://localhost:8000`. Grafana is at `http://localhost:3000`.

### 4. Targeted startup (development)

To run only the services you are actively working on:

```bash
docker compose up -d pgvector api webhooks filter ai_service payments kg-mcp-server
```

The frontend dev server can then be run locally:

```bash
cd frontend
npm install
npm run dev
```

### 5. Database schema

The schema is bootstrapped automatically on first startup by the `database/` init scripts. If you need to reset:

```bash
docker compose down -v          # destroys the pgvector volume
docker compose up -d pgvector   # re-creates and initialises
```

### 6. Filter model

The classifier model is pulled automatically by the filter container on startup from Hugging Face (`OguzhanKOG/sentinelai-bert-filter`). No manual download is required. To use a local checkpoint instead, set `MODEL_PATH` in `filter/.env` to the local directory path and mount it into the container via `docker-compose.override.yaml`.

To export to ONNX for faster inference:

```bash
docker compose exec filter python inference/export_onnx.py
```

Then set `USE_ONNX=true` in `filter/.env` and restart the filter service.

---

## Running Tests

### Filter (primary blocking gate)

```bash
pytest -q filter/tests
```

### Payments smoke tests

```bash
docker compose exec payments pytest -q
```

### Database table tests

```bash
docker compose exec api python -m pytest database/tests -q
```

### API integration tests (Windows)

```powershell
.\run_api_tests.ps1
```

### Webhooks unit tests (Windows)

```powershell
.\run_webhook_tests.ps1
```

### Resilience and load suite

```bash
cd testing
# Follow testing/README.md for configuration
```

---

## CI

CI is defined in `.github/workflows/ci.yml`. Jobs:

**Blocking (must pass for merge):**
- Frontend lint and build
- Filter tests
- Payments smoke tests
- Database table tests

**Advisory (non-blocking during integration stabilisation):**
- AI service tests
- Knowledge graph tests
- Webhooks unit tests
- API tests

---

## Monitoring

The Prometheus + Grafana stack runs alongside the application services.

**Grafana:** https://sentinelai.work/grafana/ — anonymous users have read-only viewer access. Admin login uses the credentials in `.env.grafana`.

### Scraped endpoints

| Service | Endpoint | Key signals |
|---|---|---|
| `api` | `api:8000/metrics` | HTTP latency, throughput, in-flight requests |
| `webhooks` | `webhooks:8000/metrics` | HTTP + Slack event processing rate |
| `payments` | `payments:8001/metrics` | HTTP latency, throughput |
| `ai_service` | `ai_service:8001/metrics` | HTTP + LangGraph pipeline latency and error rate |
| `filter` | `filter:9091/metrics` | gRPC call latency, batch sizes, error rate |
| `postgres-exporter` | `postgres-exporter:9187` | DB size, active connections, incident counts |

### Useful PromQL queries

```promql
# Throughput per service (req/sec, 5-min window)
rate(http_requests_total[5m])

# p95 latency per endpoint
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# gRPC error rate for filter
rate(grpc_requests_total{outcome="error"}[5m])

# LangGraph agent p95 processing time
histogram_quantile(0.95, rate(ai_pipeline_duration_seconds_bucket[5m]))
```

---

## Project Report

### 1. Problem Statement

Workplace mental health crises frequently go undetected until escalation is unavoidable. HR teams lack the tooling to triage communication signals at scale, and existing solutions either require invasive monitoring or produce noisy, low-precision alerts that erode trust. SentinelAI addresses this by providing a passive, consent-aware monitoring layer that surfaces statistically meaningful risk signals — not surveillance.

### 2. System Design

The architecture was designed around three constraints: latency (classification must not block communication delivery), privacy (no raw message content is stored beyond ephemeral processing), and modularity (each service must be independently testable and deployable).

The ingestion path is entirely asynchronous. Webhooks from Slack and Gmail are acknowledged immediately, payloads are normalised and forwarded to the filter via gRPC, and only the classification outcome and anonymised metadata are written to the database. The API and frontend never handle raw communication content.

The AI service is invoked only on incidents that cross a configurable risk threshold, keeping LLM API costs proportional to escalation volume rather than total communication volume. LangGraph was chosen over a simple chain-of-thought prompt because the assessment task requires conditional tool use (knowledge graph retrieval, historical incident lookup) that benefits from explicit graph-structured execution.

The knowledge graph MCP server externalises the evidence layer from the model weights. This allows the recommendation logic to be updated by domain experts without model retraining, and makes the agent's reasoning auditable against specific cited sources.

### 3. Machine Learning Component

The filter model is a fine-tuned `bert-base-uncased` checkpoint trained on a labelled dataset of workplace communication excerpts. Labels were assigned across three classes: benign, at-risk, and high-risk. Training used standard cross-entropy loss with class weighting to address label imbalance. The final checkpoint is published at https://huggingface.co/OguzhanKOG/sentinelai-bert-filter.

The gRPC interface accepts batched text inputs, enabling the webhooks service to batch inbound events during high-throughput periods. ONNX export is supported for deployments where sub-10ms p99 classification latency is required.

Evaluation was conducted on a held-out split. Precision on the high-risk class was prioritised over recall, as false positives (unnecessary escalations) carry a higher operational cost than false negatives in this domain.

### 4. Implementation and Service Breakdown

**API** is built on FastAPI with SQLAlchemy over PostgreSQL (pgvector extension). JWT authentication with role-based access control governs all endpoints. The metrics layer is instrumented with `prometheus-fastapi-instrumentator`.

**Webhooks** is a lightweight FastAPI service. Slack integration uses the Events API with request signature verification. Gmail integration uses push notifications via Google Pub/Sub. Both paths converge on a shared normalisation layer before gRPC dispatch.

**Filter** exposes a Protocol Buffers-defined gRPC service. The PyTorch model is loaded once at startup and held in memory. Thread safety is handled via a request queue. The ONNX path uses `onnxruntime` and bypasses the PyTorch runtime entirely.

**AI Service** is built on LangGraph with an OpenAI-compatible LLM backend. The agent graph has explicit nodes for incident context retrieval, knowledge graph tool invocation, risk assessment synthesis, and recommendation generation. All node transitions are logged for auditability.

**Payments** wraps the Stripe Python SDK. Subscription lifecycle events (created, updated, cancelled) are handled via Stripe webhooks with idempotency key enforcement.

**Knowledge Graph MCP Server** is a FastAPI service exposing MCP-spec tool endpoints. The graph is stored in a structured format and queried by embedding similarity for retrieval-augmented recommendation.

**Frontend** is a React 18 + TypeScript + Vite SPA. Routing is via React Router. State management uses React Query for server state and Zustand for local UI state. The dashboard renders incident timelines, risk trend charts (Recharts), and company/user management tables.

### 5. Testing Strategy

Testing is stratified by service. The filter service has the most comprehensive test coverage given its role as the primary ML component — tests cover classification correctness on fixed examples, gRPC interface contract, and edge cases (empty input, oversized batches). Payments tests cover the Stripe webhook handler with mocked events. Database tests verify schema integrity and CRUD correctness independently of the application layer. The `testing/` directory contains a resilience suite that exercises the API under concurrent load.

CI is deliberately split into blocking and advisory gates. Advisory jobs cover services where integration dependencies make isolated testing harder to guarantee; this avoids blocking legitimate merges while keeping visibility on integration drift.

### 6. Deployment

The live deployment at https://sentinelai.work runs on a single VM behind a reverse proxy (Caddy), with TLS termination handled automatically. All services run as Docker containers under the same Compose configuration used locally, with production `.env` values injected at runtime. The Grafana instance at https://sentinelai.work/grafana/ provides live operational observability.

### 7. Division of Work

| Area | Lead |
|---|---|
| API design and auth | Kishan Prakash, Dmytro Syzonenko |
| Filter model training and gRPC service | Oguzhan Cagirir |
| Webhooks and Slack/Gmail integration | Davyd Shtepa, Mariam Hafiz |
| AI service and LangGraph agent | Derja Sulevani, Lupupa Chansa |
| Knowledge graph and MCP server | Daria Pampukha |
| Payments and Stripe integration | Vishal Thakwani |
| Frontend | Mariam Hafiz, Dmytro Syzonenko |
| Database schema and testing | Kishan Prakash |
| Monitoring and deployment | Oguzhan Cagirir, Dmytro Syzonenko |

### 8. Reflection and Limitations

The primary technical limitation is that the filter model's training data is not drawn from a production-representative distribution. Workplace communication style varies significantly by industry, seniority, and cultural context, and the current model has not been evaluated for demographic bias. Any production deployment would require a programme of ongoing evaluation against locally labelled data.

The current architecture does not support federated or on-premise model inference. For organisations with strict data residency requirements, the filter gRPC service would need to be deployable within the customer's own network boundary — a capability that is architecturally feasible (the ONNX export path was designed with this in mind) but not yet productised.

LangGraph's execution graph is currently not persisted across restarts. Long-running assessments interrupted by a service restart are lost. Adding a durable execution backend (e.g. LangGraph Platform or a custom checkpoint store) is the most significant pending reliability improvement.

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
