# SentinelAI — Payments Service

Secure subscription billing for SentinelAI, built with **FastAPI + Stripe + PostgreSQL**.

---

## Features

| Feature | How |
|---|---|
| Subscription checkout | Stripe Checkout session (card, monthly or yearly) |
| Money into account | `invoice.paid` webhook → recorded in `payments` table |
| Subscription management | Cancel immediately or at period end |
| Refunds | Full or partial, via `POST /payments/{id}/refund` |
| Invoice history | Fetched live from Stripe with PDF links |
| Upcoming invoice | Preview next charge before it hits |
| Manual invoice send | Resend any open invoice by email |
| Customer portal | Stripe-hosted self-service billing page |
| Webhook security | Signature verification + idempotency log |

---

## Prerequisites

- **Python 3.12+**
- The main database service must be running first (creates `companies` and `subscription_plan` tables)
- A [Stripe account](https://stripe.com) (free test mode is fine)

---

## Setup

### 1. Clone & install

```bash
cd payments
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Where to find it |
|---|---|
| `DATABASE_URL` | Match the shared PostgreSQL instance |
| `STRIPE_SECRET_KEY` | [Stripe Dashboard → API keys](https://dashboard.stripe.com/apikeys) |
| `STRIPE_PUBLISHABLE_KEY` | Same page |
| `STRIPE_WEBHOOK_SECRET` | Generated in next step |
| `FRONTEND_URL` | URL of the frontend (e.g. `http://localhost:3000`) |

### 3. Set up Stripe webhook (local testing)

Install the [Stripe CLI](https://stripe.com/docs/stripe-cli), then:

```bash
stripe login
stripe listen --forward-to localhost:8001/api/v1/webhooks/stripe
```

Copy the `whsec_...` secret it prints and paste it into `.env` as `STRIPE_WEBHOOK_SECRET`.

### 4. Run the database migration

```bash
psql $DATABASE_URL -f 001_payments.sql
```

This adds Stripe columns to existing tables and creates `subscriptions`, `payments`, `stripe_events`.

### 5. Start the service

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

API docs available at: <http://localhost:8001/docs>

---

## Docker

```bash
docker build -t sentinelai-payments .
docker run --env-file .env -p 8001:8001 sentinelai-payments
```

Or use the project-level `docker-compose.yaml` where the `payments` service is already defined.

---

## API Overview

### Subscription Plans

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/plans` | List all plans |
| GET | `/api/v1/plans/{plan_id}` | Get a plan |

### Checkout & Subscriptions

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/checkout` | Create Stripe Checkout session |
| GET | `/api/v1/subscriptions/{company_id}` | Get active subscription |
| POST | `/api/v1/subscriptions/{company_id}/cancel` | Cancel subscription |

### Invoices

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/invoices/{company_id}` | Invoice history (with PDF links) |
| GET | `/api/v1/invoices/{company_id}/upcoming` | Preview next charge |
| POST | `/api/v1/invoices/{company_id}/{invoice_id}/send` | Resend open invoice by email |

### Payments & Refunds

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/payments/{company_id}` | Payment history |
| POST | `/api/v1/payments/{payment_id}/refund` | Full or partial refund |

### Other

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/portal/{company_id}` | Stripe Customer Portal session |
| POST | `/api/v1/webhooks/stripe` | Stripe webhook receiver |
| GET | `/health` | Health check |

---

## Webhook Events Handled

| Event | Action |
|---|---|
| `checkout.session.completed` | Creates subscription record in DB |
| `invoice.created` | Logged (fires each billing cycle) |
| `invoice.upcoming` | Hook for renewal reminders |
| `invoice.paid` | **Records payment** — money into account |
| `invoice.payment_failed` | Marks subscription as `past_due` |
| `customer.subscription.updated` | Syncs status/period from Stripe |
| `customer.subscription.deleted` | Marks subscription as `canceled` |
| `charge.refunded` | Syncs refund status to payment record |

---

## Monitoring

The service exposes Prometheus metrics at `GET /metrics` (port 8001). Prometheus scrapes `payments:8001/metrics` automatically.

| Metric | Type | Description |
|---|---|---|
| `http_requests_total` | Counter | All HTTP requests by method/endpoint/status |
| `http_request_duration_seconds` | Histogram | Request latency (p50/p95/p99) |
| `http_requests_in_progress` | Gauge | Concurrent requests in flight |
| `http_request_size_bytes` | Histogram | Request payload sizes |
| `http_response_size_bytes` | Histogram | Response payload sizes |

---

## How money flows in

1. User completes Stripe Checkout → `checkout.session.completed` → subscription created locally
2. Each month Stripe generates an invoice and charges the card
3. On success → `invoice.paid` fires → a `Payment` row is written to the DB with `status=succeeded`
4. On failure → `invoice.payment_failed` → subscription marked `past_due`
