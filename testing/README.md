# SentinelAI — Resilience & Load Testing

This directory contains the full resilience and load testing setup for SentinelAI.

---

## Tools

| Tool | Purpose |
|------|---------|
| **Toxiproxy** | Network fault injection (latency, bandwidth, timeouts, outages) |
| **k6** | Load and DDoS simulation |
| **Locust** | Load testing with web UI |
| **Playwright** | Behaviour validation under failures |

---

## Setup

### 1. Start the main stack
```bash
docker compose up -d
```

### 2. Start the resilience infrastructure (Toxiproxy)
```bash
cd testing
docker compose -f docker-compose.resilience.yml up -d
```

### 3. Install Playwright
```bash
npm install
npx playwright install chromium
```

---

## Running Tests

### Load Testing — k6
```bash
# Run via Docker (recommended)
docker run --rm --network sentinelai_default \
  -v $(pwd)/k6:/scripts \
  -e BASE_URL=http://api:8000 \
  -e TEST_EMAIL=loadtest@sentinelai.test \
  -e TEST_PASSWORD=loadtest123 \
  grafana/k6 run /scripts/load_test.js

# Or via npm script
npm run test:k6
```

k6 runs three scenarios:
- **Normal load** — ramp up to 10 users over 30s
- **Spike** — sudden burst to 100 users (DDoS simulation)
- **Sustained** — hold 50 concurrent users for 2 minutes

Results saved to `results/load_test_summary.json`.

### Load Testing — Locust (with UI)
```bash
npm run test:locust
# Open http://localhost:8089
```

### Resilience Testing — Chaos Scenarios
```bash
# Run all scenarios
npm run test:chaos

# Run individual scenarios
npm run test:chaos:latency    # 500ms latency injection
bash chaos/run_scenarios.sh bandwidth        # 100KB/s throttle
bash chaos/run_scenarios.sh timeout          # connection timeout
bash chaos/run_scenarios.sh down             # service outage
bash chaos/run_scenarios.sh packet_loss      # packet loss
bash chaos/run_scenarios.sh container_failure # kill pgvector
```

### Behaviour Validation — Playwright
```bash
# Run all tests
npm run test:playwright

# Run with Toxiproxy fault injection enabled
USE_TOXIPROXY=true npm run test:playwright

# Open interactive UI
npm run test:playwright:ui
```

---

## Chaos Scenarios

| Scenario | What it does | Expected result |
|----------|-------------|----------------|
| `latency` | Injects 500ms delay on API | Requests succeed but slower |
| `bandwidth` | Throttles API to 100KB/s | Large responses delayed |
| `timeout` | Times out payments connections | Payments fail gracefully |
| `down` | Disables API proxy entirely | Frontend shows error state |
| `packet_loss` | Simulates lossy webhooks network | Some requests fail |
| `container_failure` | Restarts pgvector DB | API recovers after DB comes back |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:8080` | Frontend URL |
| `API_URL` | `http://localhost:8000` | Main API URL |
| `PAYMENTS_URL` | `http://localhost:8004` | Payments service URL |
| `TOXI_URL` | `http://localhost:8474` | Toxiproxy API |
| `TEST_EMAIL` | `loadtest@sentinelai.test` | Test account email |
| `TEST_PASSWORD` | `loadtest123` | Test account password |
| `USE_TOXIPROXY` | `false` | Enable Toxiproxy tests in Playwright |

---

## Results

All results are saved to `results/`:
- `load_test_summary.json` — k6 summary
- `resilience_<timestamp>.log` — chaos scenario log
- `playwright_results.json` — Playwright test results
- `playwright_report/` — HTML report

---

## Architecture

```
Playwright/k6/Locust
        │
        ▼
  Toxiproxy (:8474)
  ├── api_proxy     → api:8000
  ├── payments_proxy → payments:8001
  └── webhooks_proxy → webhooks:8000
        │
        ▼
  SentinelAI Services
  (api, payments, webhooks, pgvector...)
```