"""
SentinelAI — Locust load testing
Run: locust -f locustfile.py --host http://localhost:8000
UI:  http://localhost:8089
"""

import json
import random
from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask


# ── Auth mixin ────────────────────────────────────────────────────────────────
class AuthMixin:
    token: str | None = None

    def login(self):
        res = self.client.post(
            "/auth/login",
            json={"email": "loadtest@sentinelai.test", "password": "loadtest123"},
            name="/auth/login",
        )
        if res.status_code == 200:
            self.token = res.json().get("access_token")
        else:
            self.token = None

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}


# ── Anonymous user (landing / signup flow) ────────────────────────────────────
class AnonymousUser(HttpUser):
    """Simulates unauthenticated traffic: health checks and plan browsing."""

    wait_time = between(1, 3)
    weight = 3  # 30% of users

    @task(5)
    def health_check(self):
        self.client.get("/health", name="/health")

    @task(3)
    def browse_plans(self):
        self.client.get("/plans", name="/plans")

    @task(1)
    def metrics(self):
        self.client.get("/metrics", name="/metrics")


# ── Authenticated HR user ─────────────────────────────────────────────────────
class HRUser(AuthMixin, HttpUser):
    """Simulates a logged-in HR admin browsing the dashboard."""

    wait_time = between(2, 5)
    weight = 7  # 70% of users

    def on_start(self):
        self.login()
        if not self.token:
            raise RescheduleTask()

    @task(5)
    def view_dashboard(self):
        self.client.get(
            "/usage?start=2026-01-01&end=2026-04-06",
            headers=self.auth_headers,
            name="/usage",
        )

    @task(4)
    def view_incidents(self):
        skip = random.randint(0, 5) * 10
        self.client.get(
            f"/incidents?skip={skip}&limit=20",
            headers=self.auth_headers,
            name="/incidents",
        )

    @task(3)
    def incident_stats(self):
        self.client.get(
            "/incidents/stats",
            headers=self.auth_headers,
            name="/incidents/stats",
        )

    @task(3)
    def view_employees(self):
        self.client.get(
            "/integrations/slack/users",
            headers=self.auth_headers,
            name="/integrations/slack/users",
        )

    @task(2)
    def view_company(self):
        self.client.get(
            "/companies/me",
            headers=self.auth_headers,
            name="/companies/me",
        )

    @task(2)
    def view_integrations(self):
        self.client.get(
            "/integrations",
            headers=self.auth_headers,
            name="/integrations",
        )

    @task(1)
    def view_team(self):
        self.client.get(
            "/users",
            headers=self.auth_headers,
            name="/users",
        )

    @task(1)
    def view_subscription(self):
        self.client.get(
            "/subscriptions/current",
            headers=self.auth_headers,
            name="/subscriptions/current",
        )


# ── Event hooks ───────────────────────────────────────────────────────────────
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("=== SentinelAI Load Test Starting ===")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats.total
    print(f"""
=== SentinelAI Load Test Complete ===
Total requests:  {stats.num_requests}
Failed:          {stats.num_failures}
Avg latency:     {stats.avg_response_time:.0f}ms
p95 latency:     {stats.get_response_time_percentile(0.95):.0f}ms
RPS:             {stats.current_rps:.1f}
=====================================
    """)