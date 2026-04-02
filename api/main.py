from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.error_handler import register_error_handlers
from api.middleware.metrics import PrometheusMiddleware, metrics_endpoint
from api.routers import auth, company, integrations, messages, plans, slack, subscriptions, usage, users

app = FastAPI(title="SentinelAI API", version="0.1.0")
register_error_handlers(app)

app.add_middleware(PrometheusMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_route("/metrics", metrics_endpoint, methods=["GET"])

app.include_router(auth.router)
app.include_router(company.router)
app.include_router(integrations.router)
app.include_router(messages.router)
app.include_router(plans.router)
app.include_router(slack.router)
app.include_router(subscriptions.router)
app.include_router(usage.router)
app.include_router(users.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
