# AI Service

Mental health risk assessment agent using LangGraph.

## Structure

- **agent.py** - FastAPI app exposing the LangGraph agent
- **prompts/** - Versioned system prompts for mental health assessment
- **schema/** - Pydantic schemas for state and output validation
- **services/** - Prompt loading and MCP integration services
- **tests/** - Test suite for all components

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn agent:app --host 0.0.0.0 --port 8001
```

## Docker

```bash
docker-compose up ai_service
```

## Test

```bash
pytest tests/
```

## Monitoring

The service exposes Prometheus metrics at `GET /metrics` (port 8001).

| Metric | Type | Description |
|---|---|---|
| `http_requests_total` | Counter | All HTTP requests by method/endpoint/status |
| `http_request_duration_seconds` | Histogram | HTTP request latency (p50/p95/p99) |
| `http_requests_in_progress` | Gauge | Concurrent requests in flight |
| `ai_pipeline_calls_total` | Counter | LangGraph agent invocations, labelled `mode` (single/batch) + `outcome` |
| `ai_pipeline_duration_seconds` | Histogram | End-to-end agent processing time including all LLM calls |

The `ai_pipeline_*` metrics are particularly useful for tracking LLM latency and error rates independently of the HTTP layer.
