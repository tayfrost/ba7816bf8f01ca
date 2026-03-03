"""
SentinelAI Payments Service — FastAPI entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.payments import router as payments_router
from app.api.webhooks.stripe_webhook import router as webhook_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, init_db
from app.services.seed_service import seed_plans

logger = logging.getLogger(__name__)
settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Payments Service...")
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_plans(session)
    logger.info("Payments Service ready")
    yield
    logger.info("Shutting down Payments Service...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Secure payment processing for SentinelAI.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments_router, prefix="/api/v1", tags=["Payments"])
app.include_router(webhook_router, prefix="/api/v1/webhooks", tags=["Webhooks"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "payments", "version": settings.APP_VERSION}
