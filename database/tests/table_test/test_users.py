import pytest
from database.services import users_crud as crud  
from database.services import companies_crud as company_crud 
from database.services import subscription_plan_crud as sp_crud
from database.services import subscriptions_crud as subs_crud
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone

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

def _mk_company(db_session, name="UsersCo", with_subscription=True):
    company = company_crud.create_company(name, session=db_session)

    if with_subscription:
        plan = sp_crud.create_subscription_plan(
            plan_name=f"{name} Plan",
            price_pennies=1000,
            seat_limit=10,
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

@pytest.mark.parametrize("role", ["", "owner", "ADMIN"])
def test_create_user_invalid_role_raises_valueerror(db_session, role):
    company = _mk_company(db_session)
    with pytest.raises(ValueError):
        crud.create_user(company.company_id, role=role, session=db_session)

@pytest.mark.parametrize("status", ["", "removed", "ACTIVE"])
def test_create_user_invalid_status_raises_valueerror(db_session, status):
    company = _mk_company(db_session)
    with pytest.raises(ValueError):
        crud.create_user(company.company_id, role="viewer", status=status, session=db_session)

def test_create_user_success(db_session):
    company = _mk_company(db_session)
    u = crud.create_user(
        company.company_id,
        role="viewer",
        status="active",
        display_name="Bob",
        session=db_session,
    )
    assert u.user_id is not None
    assert u.company_id == company.company_id
    assert u.role == "viewer"
    assert u.status == "active"
    assert u.display_name == "Bob"
    assert u.deleted_at is None

def test_get_user_by_id_and_list_users(db_session):
    company = _mk_company(db_session)
    u1 = crud.create_user(company.company_id, role="viewer", display_name="A", session=db_session)
    u2 = crud.create_user(company.company_id, role="admin", display_name="B", session=db_session)

    got = crud.get_user_by_id(company.company_id, u1.user_id, session=db_session)
    assert got is not None
    assert got.user_id == u1.user_id

    users = crud.list_users(company.company_id, session=db_session)
    assert len(users) == 2
    assert {u.user_id for u in users} == {u1.user_id, u2.user_id}

def test_update_user_fields(db_session):
    company = _mk_company(db_session)
    u = crud.create_user(company.company_id, role="viewer", status="active", display_name="Old", session=db_session)

    updated = crud.update_user(
        company.company_id,
        u.user_id,
        display_name="New",
        role="biller",
        status="inactive",
        session=db_session,
    )
    assert updated is not None
    assert updated.display_name == "New"
    assert updated.role == "biller"
    assert updated.status == "inactive"

@pytest.mark.parametrize("kwargs", [{"role": "boss"}, {"status": "removed"}])
def test_update_user_invalid_inputs_raise_valueerror(db_session, kwargs):
    company = _mk_company(db_session)
    u = crud.create_user(company.company_id, role="viewer", session=db_session)

    with pytest.raises(ValueError):
        crud.update_user(company.company_id, u.user_id, session=db_session, **kwargs)

def test_update_user_not_found_returns_none(db_session):
    company = _mk_company(db_session)
    missing_id = crud.create_user(company.company_id, role="viewer", session=db_session).user_id

    # hard delete it so update won't find it
    assert crud.hard_delete_user(company.company_id, missing_id, session=db_session) is True

    res = crud.update_user(company.company_id, missing_id, display_name="X", session=db_session)
    assert res is None

def test_soft_delete_and_restore_user(db_session):
    company = _mk_company(db_session)
    u = crud.create_user(company.company_id, role="viewer", session=db_session)

    assert crud.soft_delete_user(company.company_id, u.user_id, session=db_session) is True

    # default get excludes deleted
    assert crud.get_user_by_id(company.company_id, u.user_id, session=db_session) is None

    # but include_deleted sees it
    deleted = crud.get_user_by_id(company.company_id, u.user_id, include_deleted=True, session=db_session)
    assert deleted is not None
    assert deleted.deleted_at is not None

    assert crud.restore_user(company.company_id, u.user_id, session=db_session) is True
    restored = crud.get_user_by_id(company.company_id, u.user_id, session=db_session)
    assert restored is not None
    assert restored.deleted_at is None

def test_hard_delete_user_success(db_session):
    company = _mk_company(db_session)
    u = crud.create_user(company.company_id, role="viewer", session=db_session)

    ok = crud.hard_delete_user(company.company_id, u.user_id, session=db_session)
    assert ok is True
    assert crud.get_user_by_id(company.company_id, u.user_id, include_deleted=True, session=db_session) is None


