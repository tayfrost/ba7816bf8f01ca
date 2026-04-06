# SentinelAI API

FastAPI backend for SentinelAI — a workplace wellbeing monitoring platform.

## Quick Start

### With Docker Compose (recommended)

```bash
docker compose up api pgvector -d
```

The API will be available at `http://localhost:8000`.

### Locally

```bash
cd api
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

## Environment Variables

Copy the example and fill in your values:

```bash
cp api/.env.example api/.env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/sentinelai` |
| `SECRET_KEY` | JWT signing secret | `change-me-in-production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry in minutes | `1440` (24h) |

## Interacting with the API

The API uses JWT Bearer tokens for auth. Most endpoints require you to register first, then pass the token in all subsequent requests.

### 1. Register a new account

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@mycompany.com",
    "password": "securepassword123",
    "name": "John",
    "surname": "Doe",
    "company_name": "My Company",
    "plan_id": 1
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

Save the `access_token` — you'll need it for everything below.

### 2. Login (if you already have an account)

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@mycompany.com",
    "password": "securepassword123"
  }'
```

### 3. Use the token

Pass it as a Bearer token in the `Authorization` header:

```bash
TOKEN="eyJhbGciOiJIUzI1NiIs..."

# Get your user info
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Get your company
curl http://localhost:8000/companies/me \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Common operations

**List subscription plans (no auth needed):**
```bash
curl http://localhost:8000/plans
```

**List users in your company:**
```bash
curl http://localhost:8000/users \
  -H "Authorization: Bearer $TOKEN"
```

**Invite a new user (admin/biller only):**
```bash
curl -X POST "http://localhost:8000/users/invite?email=jane@mycompany.com&name=Jane&surname=Smith&role=viewer" \
  -H "Authorization: Bearer $TOKEN"
```

**Get flagged incidents:**
```bash
curl http://localhost:8000/incidents \
  -H "Authorization: Bearer $TOKEN"
```

**Get incident stats (grouped by reason):**
```bash
curl http://localhost:8000/incidents/stats \
  -H "Authorization: Bearer $TOKEN"
```

**Get dashboard chart data:**
```bash
curl "http://localhost:8000/usage?start=2026-01-01&end=2026-03-29" \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "range": {"start": "2026-01-01", "end": "2026-03-29"},
  "series": [
    {
      "key": "messagesFlagged",
      "label": "Messages flagged",
      "points": [{"date": "2026-03-15", "value": 12}, {"date": "2026-03-16", "value": 8}]
    },
    {
      "key": "riskScore",
      "label": "Risk score",
      "points": [{"date": "2026-03-15", "value": 47}, {"date": "2026-03-16", "value": 31}]
    },
    {
      "key": "harassment",
      "label": "Harassment",
      "points": [{"date": "2026-03-15", "value": 3}, {"date": "2026-03-16", "value": 1}]
    }
  ]
}
```

**Check integration status:**
```bash
curl http://localhost:8000/integrations \
  -H "Authorization: Bearer $TOKEN"
```

**List connected Slack workspaces:**
```bash
curl http://localhost:8000/integrations/slack/workspaces \
  -H "Authorization: Bearer $TOKEN"
```

**List monitored Slack users (Employees page):**
```bash
curl http://localhost:8000/integrations/slack/users \
  -H "Authorization: Bearer $TOKEN"
```

**Soft-delete your company (biller only):**
```bash
curl -X DELETE http://localhost:8000/companies/me \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Interactive docs

FastAPI auto-generates interactive API docs. With the server running, open:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

You can test endpoints directly from the browser. Click "Authorize" and paste your Bearer token to test authenticated routes.

## All Endpoints

### Auth
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | No | Register new user + company, returns JWT |
| POST | `/auth/login` | No | Login, returns JWT |
| GET | `/auth/me` | Yes | Get current user info |

### Companies
| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| POST | `/companies` | No | — | Create company |
| GET | `/companies/me` | Yes | Any | Get your company |
| PATCH | `/companies/me` | Yes | biller, admin | Update company name |
| DELETE | `/companies/me` | Yes | biller | Soft-delete company |

### Users
| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `/users` | Yes | Any | List company users |
| GET | `/users/{user_id}` | Yes | Any | Get specific user |
| POST | `/users/invite` | Yes | admin, biller | Invite new user |
| PATCH | `/users/{user_id}` | Yes | admin, biller | Update user role/name |
| DELETE | `/users/{user_id}` | Yes | admin, biller | Deactivate user |

### Plans
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/plans` | No | List all subscription plans |
| GET | `/plans/{plan_id}` | No | Get specific plan |
| POST | `/plans` | Yes (admin/biller) | Create plan |
| PATCH | `/plans/{plan_id}` | Yes (admin/biller) | Update plan |
| DELETE | `/plans/{plan_id}` | Yes (admin/biller) | Delete plan |

### Subscriptions
| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `/subscriptions/plans` | No | — | List plans |
| GET | `/subscriptions/current` | Yes | Any | Get active subscription |
| POST | `/subscriptions` | Yes | biller | Create subscription |

### Incidents
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/incidents` | Yes | List flagged incidents (paginated: `?skip=0&limit=50`) |
| GET | `/incidents/stats` | Yes | Aggregate stats by class_reason |
| GET | `/incidents/{incident_id}` | Yes | Get single incident |

### Dashboard
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/usage?start=...&end=...` | Yes | Chart data for frontend dashboard |

### Integrations
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/integrations` | Yes | Status of all providers (slack, gmail, outlook) |
| POST | `/integrations/{provider}/start` | Yes (admin/biller) | Get OAuth URL for provider |
| DELETE | `/integrations/{provider}` | Yes (admin/biller) | Disconnect provider |

### Slack
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/integrations/slack/install` | Yes (admin/biller) | Store workspace after OAuth |
| GET | `/integrations/slack/workspaces` | Yes | List connected workspaces |
| DELETE | `/integrations/slack/workspaces/{id}` | Yes (admin/biller) | Remove workspace |
| GET | `/integrations/slack/users` | Yes | List monitored Slack users |

### System
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Health check |
| GET | `/metrics` | No | Prometheus metrics |

## Access Control

Three roles: **biller** (company owner), **admin**, **viewer**.

- Biller is assigned automatically to whoever registers the company
- Only biller can delete the company or manage billing
- Admin and biller can invite/deactivate users
- Viewer can only read data
- You can't remove the last admin/biller from a company (prevents lockout)

## Soft-Delete Pattern

When a company is soft-deleted (`DELETE /companies/me`):
- `deleted_at` timestamp is set on the company
- All user roles in that company are set to `inactive`
- Login attempts return 401
- All authenticated endpoints return 401
- The company and its data still exist in the database but are invisible to the API

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
