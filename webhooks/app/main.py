"""
Main application file for the webhooks service.

Orchestration only — routes are registered from controllers, business
logic lives in services, data structures in schemas.
"""

import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler

from app.controllers.slack_controller import router as slack_router
from app.controllers.gmail_controller import router as gmail_router
from app.middleware.metrics import setup_metrics
from app.services.watch_renewal_service import renew_expiring_watches

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler()
_scheduler.add_job(
    renew_expiring_watches,
    trigger="interval",
    hours=48,
    id="gmail_watch_renewal",
    replace_existing=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _scheduler.start()
    logger.info("Gmail watch renewal scheduler started (interval=48h)")
    try:
        summary = renew_expiring_watches()
        logger.info(f"Startup watch renewal: {summary}")
    except Exception as e:
        logger.error(f"Startup watch renewal failed: {e}")
    yield
    _scheduler.shutdown(wait=False)
    logger.info("Gmail watch renewal scheduler stopped")


app = FastAPI(lifespan=lifespan)

setup_metrics(app)

app.include_router(slack_router)
app.include_router(gmail_router)