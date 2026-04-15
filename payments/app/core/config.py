"""
Application configuration loaded from environment variables.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "SentinelAI Payments Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str  # Must be set via .env — no insecure default

    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    FRONTEND_URL: str = "http://localhost:3000"
    PAYMENTS_SERVICE_URL: str = "http://localhost:8001"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
