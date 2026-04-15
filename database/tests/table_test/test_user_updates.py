import pytest
from datetime import datetime, timedelta, timezone

from database.services import users_crud as crud
from database.services import companies_crud as company_crud
from database.services import subscription_plan_crud as sp_crud
from database.services import subscriptions_crud as subs_crud
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False)

@pytest.fixture
def db_session():
    connection = crud.engine.connect()
    outer_transaction = connection.begin()

    session = TestingSessionLocal(bind=connection)

    nested_transaction = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested_transaction
        if connection.closed:
            return
        if not nested_transaction.is_active and connection.in_transaction():
            nested_transaction = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if outer_transaction.is_active:
            outer_transaction.rollback()
        connection.close()

SEAT_LIMIT = 10


def _mk_company(db_session, name: str):
    company = company_crud.create_company(name, session=db_session)
    plan = sp_crud.create_subscription_plan(
        plan_name=f"{name} Plan",
        price_pennies=1000,
        seat_limit=SEAT_LIMIT,
        currency="GBP",
        session=db_session,
    )
    now = datetime.now(timezone.utc)
    subs_crud.create_subscription(
        company.company_id,
        plan.plan_id,
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        session=db_session,
    )
    return company

def _count_active_users(session, company_id: int) -> int:
    return sum(
        1
        for u in crud.list_users(company_id, session=session)
        if u.deleted_at is None and u.status == "active"
    )

def test_create_user_blocks_when_seat_limit_reached(db_session):
    company = _mk_company(db_session, name="SeatLimitCreateCo")
    company_id = company.company_id
    active_before = _count_active_users(db_session, company_id)

    users_to_create = max(0, SEAT_LIMIT - active_before)

    created_users = []
    for i in range(users_to_create):
        user = crud.create_user(
            company_id,
            role="viewer",
            status="active",
            display_name=f"Seat Fill User {i}",
            session=db_session,
        )
        created_users.append(user)

    active_now = _count_active_users(db_session, company_id)
    assert active_now == SEAT_LIMIT

    with pytest.raises(RuntimeError, match="Seat limit reached"):
        crud.create_user(
            company_id,
            role="viewer",
            status="active",
            display_name="Should Fail",
            session=db_session,
        )

def test_update_user_blocks_activation_when_seat_limit_reached(db_session):
    company = _mk_company(db_session, name="SeatLimitUpdateCo")
    company_id = company.company_id
    active_before = _count_active_users(db_session, company_id)

    users_to_create = max(0, SEAT_LIMIT - active_before)

    for i in range(users_to_create):
        crud.create_user(
            company_id,
            role="viewer",
            status="active",
            display_name=f"Active Fill User {i}",
            session=db_session,
        )

    active_now = _count_active_users(db_session, company_id)
    assert active_now == SEAT_LIMIT

    inactive_user = crud.create_user(
        company_id,
        role="viewer",
        status="inactive",
        display_name="Inactive User",
        session=db_session,
    )

    with pytest.raises(RuntimeError, match="Seat limit reached"):
        crud.update_user(
            company_id,
            inactive_user.user_id,
            status="active",
            session=db_session,
        )