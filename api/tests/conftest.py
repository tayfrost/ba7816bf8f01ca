import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.schema import CheckConstraint

from api.dependencies import get_db
from api.main import app
from api.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _strip_check_constraints(target, connection, **kw):
    """Remove PostgreSQL-specific CHECK constraints for SQLite testing."""
    if connection.dialect.name == "sqlite":
        for table in target.tables.values():
            table.constraints = {
                c for c in table.constraints if not isinstance(c, CheckConstraint)
            }


# Strip check constraints before table creation on SQLite
event.listen(Base.metadata, "before_create", _strip_check_constraints)


async def _seed_default_plan(session: AsyncSession):
    """Seed a default subscription plan so registration tests work."""
    from api.models.subscription_plan import SubscriptionPlan

    plan = SubscriptionPlan(
        plan_id=1,
        plan_name="Free",
        plan_cost_pennies=0,
        currency="GBP",
        max_employees=10,
    )
    session.add(plan)
    await session.commit()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        await _seed_default_plan(session)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
