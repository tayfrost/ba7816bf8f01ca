from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str  # Must be set via .env — no insecure default
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
