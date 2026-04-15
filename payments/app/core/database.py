"""
Async database engine and session factory.
Uses SQLAlchemy 2.0 async API with asyncpg driver.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.models import Base

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """
    Create only NEW payment tables (subscriptions, payments, stripe_events).
    Does NOT touch existing tables (subscription_plans, companies, etc.).
    Also adds Stripe columns to existing tables via ALTER TABLE.
    """
    async with engine.begin() as conn:
        # Create new tables only (checkfirst=True avoids touching existing ones)
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        # Add Stripe columns to existing tables if they don't exist yet
        await conn.execute(
            __import__("sqlalchemy").text("""
                DO $$
                BEGIN
                    -- Add stripe_customer_id to companies
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'companies' AND column_name = 'stripe_customer_id'
                    ) THEN
                        ALTER TABLE companies ADD COLUMN stripe_customer_id TEXT UNIQUE;
                    END IF;

                    -- Add stripe_price_id_monthly to subscription_plans
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'subscription_plans' AND column_name = 'stripe_price_id_monthly'
                    ) THEN
                        ALTER TABLE subscription_plans ADD COLUMN stripe_price_id_monthly TEXT;
                    END IF;

                    -- Add stripe_price_id_yearly to subscription_plans
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'subscription_plans' AND column_name = 'stripe_price_id_yearly'
                    ) THEN
                        ALTER TABLE subscription_plans ADD COLUMN stripe_price_id_yearly TEXT;
                    END IF;
                END $$;
            """)
        )
