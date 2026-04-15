import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const errorRate = new Rate("errors");
const apiLatency = new Trend("api_latency");

// ── Config ────────────────────────────────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const PAYMENTS_URL = __ENV.PAYMENTS_URL || "http://localhost:8004";

// Test credentials — override via env vars
const TEST_EMAIL = __ENV.TEST_EMAIL || "loadtest@sentinelai.test";
const TEST_PASSWORD = __ENV.TEST_PASSWORD || "loadtest123";

// ── Stages ────────────────────────────────────────────────────────────────────
export const options = {
  scenarios: {
    // Scenario 1: Ramp up normal load
    normal_load: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 10 },  // ramp up
        { duration: "1m",  target: 10 },  // hold
        { duration: "15s", target: 0  },  // ramp down
      ],
      tags: { scenario: "normal" },
    },

    // Scenario 2: Spike / DDoS simulation
    spike: {
      executor: "ramping-vus",
      startVUs: 0,
      startTime: "2m",
      stages: [
        { duration: "10s", target: 100 }, // sudden spike
        { duration: "30s", target: 100 }, // hold spike
        { duration: "10s", target: 0   }, // drop
      ],
      tags: { scenario: "spike" },
    },

    // Scenario 3: Sustained high load
    sustained: {
      executor: "constant-vus",
      vus: 50,
      duration: "2m",
      startTime: "3m30s",
      tags: { scenario: "sustained" },
    },
  },

  thresholds: {
    http_req_duration: ["p(95)<2000"], // 95% of requests under 2s
    http_req_failed:   ["rate<0.05"],  // less than 5% errors
    errors:            ["rate<0.05"],
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function getToken() {
  const res = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email: TEST_EMAIL, password: TEST_PASSWORD }),
    { headers: { "Content-Type": "application/json" } }
  );

  if (res.status === 200) {
    return res.json("access_token");
  }
  return null;
}

function authHeaders(token) {
  return {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  };
}

// ── Main test ─────────────────────────────────────────────────────────────────
export default function () {
  // 1. Health check (no auth)
  const health = http.get(`${BASE_URL}/health`);
  check(health, { "health ok": (r) => r.status === 200 });
  errorRate.add(health.status !== 200);
  apiLatency.add(health.timings.duration);

  // 2. Plans endpoint (no auth)
  const plans = http.get(`${BASE_URL}/plans`);
  check(plans, {
    "plans status 200": (r) => r.status === 200,
    "plans returns array": (r) => Array.isArray(r.json()),
  });
  errorRate.add(plans.status !== 200);

  // 3. Auth → login
  const token = getToken();
  if (!token) {
    errorRate.add(1);
    sleep(1);
    return;
  }

  const headers = authHeaders(token);

  // 4. Get current user
  const me = http.get(`${BASE_URL}/auth/me`, headers);
  check(me, { "me status 200": (r) => r.status === 200 });
  errorRate.add(me.status !== 200);
  apiLatency.add(me.timings.duration);

  // 5. Get company
  const company = http.get(`${BASE_URL}/companies/me`, headers);
  check(company, { "company status 200": (r) => r.status === 200 });
  errorRate.add(company.status !== 200);

  // 6. Get incidents (paginated)
  const incidents = http.get(`${BASE_URL}/incidents?skip=0&limit=20`, headers);
  check(incidents, { "incidents status 200": (r) => r.status === 200 });
  errorRate.add(incidents.status !== 200);
  apiLatency.add(incidents.timings.duration);

  // 7. Get usage/dashboard data
  const usage = http.get(
    `${BASE_URL}/usage?start=2026-01-01&end=2026-04-06`,
    headers
  );
  check(usage, { "usage status 200": (r) => r.status === 200 });
  errorRate.add(usage.status !== 200);
  apiLatency.add(usage.timings.duration);

  // 8. Get integrations
  const integrations = http.get(`${BASE_URL}/integrations`, headers);
  check(integrations, { "integrations status 200": (r) => r.status === 200 });
  errorRate.add(integrations.status !== 200);

  sleep(1);
}

// ── Summary ───────────────────────────────────────────────────────────────────
export function handleSummary(data) {
  return {
    "results/load_test_summary.json": JSON.stringify(data, null, 2),
    stdout: `
=== SentinelAI Load Test Summary ===
Total requests:     ${data.metrics.http_reqs.values.count}
Failed requests:    ${data.metrics.http_req_failed.values.passes}
Avg latency:        ${Math.round(data.metrics.http_req_duration.values.avg)}ms
p95 latency:        ${Math.round(data.metrics.http_req_duration.values["p(95)"])}ms
p99 latency:        ${Math.round(data.metrics.http_req_duration.values["p(99)"])}ms
=====================================
    `,
  };
}