import pytest
from database.services import users_crud as crud 
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import inspect

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

TEST_COMPANY_ID = 47
SEAT_LIMIT = 10

def _count_active_users(session, company_id: int) -> int:
    return sum(
        1
        for u in crud.list_users(company_id, session=session)
        if u.deleted_at is None and u.status == "active"
    )

def test_create_user_blocks_when_seat_limit_reached(db_session):
    active_before = _count_active_users(db_session, TEST_COMPANY_ID)

    users_to_create = max(0, SEAT_LIMIT - active_before)

    created_users = []
    for i in range(users_to_create):
        user = crud.create_user(
            TEST_COMPANY_ID,
            role="viewer",
            status="active",
            display_name=f"Seat Fill User {i}",
            session=db_session,
        )
        created_users.append(user)

    active_now = _count_active_users(db_session, TEST_COMPANY_ID)
    assert active_now == SEAT_LIMIT

    with pytest.raises(RuntimeError, match="Seat limit reached"):
        crud.create_user(
            TEST_COMPANY_ID,
            role="viewer",
            status="active",
            display_name="Should Fail",
            session=db_session,
        )

def test_update_user_blocks_activation_when_seat_limit_reached(db_session):
    active_before = _count_active_users(db_session, TEST_COMPANY_ID)

    users_to_create = max(0, SEAT_LIMIT - active_before)

    for i in range(users_to_create):
        crud.create_user(
            TEST_COMPANY_ID,
            role="viewer",
            status="active",
            display_name=f"Active Fill User {i}",
            session=db_session,
        )

    active_now = _count_active_users(db_session, TEST_COMPANY_ID)
    assert active_now == SEAT_LIMIT

    inactive_user = crud.create_user(
        TEST_COMPANY_ID,
        role="viewer",
        status="inactive",
        display_name="Inactive User",
        session=db_session,
    )

    with pytest.raises(RuntimeError, match="Seat limit reached"):
        crud.update_user(
            TEST_COMPANY_ID,
            inactive_user.user_id,
            status="active",
            session=db_session,
        )