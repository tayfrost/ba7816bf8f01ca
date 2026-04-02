# SentinelAI API

FastAPI backend for SentinelAI — a workplace wellbeing monitoring platform.

## Quick Start

### With Docker Compose (recommended)

```bash
docker-compose up api pgvector
```

The API will be available at `http://localhost:8002`.

### Locally

```bash
cd api
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/sentinelai` |
| `SECRET_KEY` | JWT signing secret | `change-me-in-production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry in minutes | `1440` (24h) |

## API Endpoints

### Auth
- `POST /auth/register` — Register new user + company
- `POST /auth/login` — Login, returns JWT
- `GET /auth/me` — Get current user info

### Companies
- `POST /companies` — Create company (used during registration)
- `GET /companies/me` — Get your company
- `PATCH /companies/me` — Update company (biller only)
- `DELETE /companies/me` — Soft delete company (biller only)

### Users
- `GET /users` — List company users
- `GET /users/{user_id}` — Get specific user
- `POST /users/invite` — Invite user (admin/biller only)
- `PATCH /users/{user_id}` — Update user role (admin/biller only)
- `DELETE /users/{user_id}` — Deactivate user (admin/biller only)

### Subscriptions
- `GET /subscriptions/plans` — List available plans (public)
- `GET /subscriptions/current` — Get active subscription
- `POST /subscriptions` — Create/change subscription (biller only)

### Slack Integration
- `POST /integrations/slack/install` — Install workspace (biller/admin)
- `GET /integrations/slack/workspaces` — List connected workspaces
- `DELETE /integrations/slack/workspaces/{id}` — Revoke workspace
- `GET /integrations/slack/accounts` — List tracked accounts

### Messages
- `GET /messages` — List flagged messages (paginated)
- `GET /messages/{message_id}` — Get message with scores
- `GET /messages/stats` — Aggregate stats by severity/category

### Health
- `GET /health` — Health check

## Soft-Delete Access Control

Deleted companies are invisible to the API. When a company is soft-deleted:
- `deleted_at` is set on the company record
- All users in that company are set to `status='inactive'`
- Login attempts are rejected
- All authenticated endpoints return 401

This ensures that deleted companies cannot access any data.

## Running Tests

```bash
pip install pytest pytest-asyncio httpx aiosqlite
cd api
pytest tests/ -v
```

## Database Migrations

```bash
cd api
alembic upgrade head
```
