# Webhooks Service

Sits between Slack / Gmail and the SentinelAI database. Receives real-time messages via webhook, runs them through the AI filter, and stores flagged incidents with classification scores.

---

## Structure

```text
webhooks/
├── app/
│   ├── controllers/   # HTTP routing — Slack and Gmail endpoints
│   ├── services/      # Business logic — OAuth, message pipeline, filter client, DB delegation, watch renewal
│   ├── middleware/    # Prometheus metrics
│   └── schemas/       # Pydantic models
├── Dockerfile
├── Dockerfile.test
├── pytest.ini
└── requirements.txt
```

---

## Prerequisites

Create `webhooks/.env` before running:

```env
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
SLACK_REDIRECT_URI=https://sentinelai.work/slack/oauth/callback
SLACK_SIGNING_SECRET=

GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_PUBSUB_TOPIC=projects/<project>/topics/<topic>

BASE_URL=https://sentinelai.work
GMAIL_WEBHOOK_ENDPOINT=https://sentinelai.work/gmail/events

DATABASE_URL=postgresql+psycopg://postgres:postgres@pgvector:5432/sentinelai
FILTER_SERVICE_HOST=filter:50051
```

---

## Running via Docker Compose

The service requires `filter` and `pgvector` to be running. Minimum Docker Compose config:

```yaml
webhooks:
  build:
    context: .
    dockerfile: webhooks/Dockerfile
  ports:
    - "9000:8000"
  env_file:
    - ./webhooks/.env
  depends_on:
    - pgvector
    - filter
  restart: unless-stopped
```

Start just the webhooks stack:

```bash
docker compose up --build webhooks filter pgvector
```

---

## Running Tests

Unit tests require no live services — all external dependencies are mocked.

**Via Docker** — run from the repo root:

```bash
sudo docker build -f webhooks/Dockerfile.test -t webhooks-test .
sudo docker run --rm webhooks-test
```

**To test without docker:**

```bash
cd webhooks
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m pytest app/tests/ -v --ignore=app/tests/test_filter_integration.py
```

Integration tests (require the filter service running via Docker Compose):

```bash
sudo docker compose up filter
python3 -m pytest app/tests/test_filter_integration.py -v
```
