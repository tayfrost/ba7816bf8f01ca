import pytest
from database.db_service.utils import subscription_plan_crud as crud 
from sqlalchemy import event

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
    
@pytest.mark.parametrize(
    "plan_name,price_pennies,seat_limit,currency",
    [
        (" ", 0, 5, "GBP"),          # name too short after trim
        ("A", 0, 5, "GBP"),          # name length 1
        ("Valid", -1, 5, "GBP"),     # negative price
        ("Valid", 0, 0, "GBP"),      # seat_limit <= 0
        ("Valid", 0, 5, "GB"),       # currency not length 3
    ],
)

def test_create_subscription_plan_invalid_inputs(db_session, plan_name, price_pennies, seat_limit, currency):
    with pytest.raises(ValueError):
        crud.create_subscription_plan(
            plan_name=plan_name,
            price_pennies=price_pennies,
            seat_limit=seat_limit,
            currency=currency,
            session=db_session,
        )

def test_create_subscription_plan_currency_none_defaults_to_gbp(db_session):
    plan = crud.create_subscription_plan(
        plan_name="Starter",
        price_pennies=0,
        seat_limit=5,
        currency=None,  # should default to GBP
        session=db_session,
    )
    assert plan.plan_id is not None
    assert plan.plan_name == "Starter"
    assert plan.price_pennies == 0
    assert plan.seat_limit == 5
    assert plan.currency == "GBP"

def test_create_subscription_plan_duplicate_name_raises_runtimeerror(db_session):
    crud.create_subscription_plan(
        plan_name="Pro",
        price_pennies=1200,
        seat_limit=10,
        currency="GBP",
        session=db_session,
    )

    with pytest.raises(RuntimeError):
        crud.create_subscription_plan(
            plan_name="Pro",  # duplicate
            price_pennies=1500,
            seat_limit=15,
            currency="GBP",
            session=db_session,
        )

def test_list_subscription_plans_ordering(db_session):
    # price asc, seat asc, name asc
    crud.create_subscription_plan("Bi", 200, 10, "GBP", session=db_session)
    crud.create_subscription_plan("Basic", 200, 10, "GBP", session=db_session)
    crud.create_subscription_plan("Plus", 200, 5, "GBP", session=db_session)
    crud.create_subscription_plan("Alpha", 200, 5, "GBP", session=db_session)
    crud.create_subscription_plan("Free", 0, 1, "GBP", session=db_session)

    plans = crud.list_subscription_plans(session=db_session)
    names = [p.plan_name for p in plans]

    target_names = {"Free", "Alpha", "Plus", "Basic", "Bi"}
    filtered_names = [name for name in names if name in target_names]

    assert filtered_names == ["Free", "Alpha", "Plus", "Basic", "Bi"]

def test_get_subscription_plan_by_name_found_and_not_found(db_session):
    crud.create_subscription_plan("Team", 999, 25, "GBP", session=db_session)

    found = crud.get_subscription_plan_by_name("Team", session=db_session)
    assert found is not None
    assert found.plan_name == "Team"

    not_found = crud.get_subscription_plan_by_name("DoesNotExist", session=db_session)
    assert not_found is None

def test_get_subscription_plan_by_id(db_session):
    plan = crud.create_subscription_plan("Enterprise", 9999, 250, "GBP", session=db_session)

    fetched = crud.get_subscription_plan_by_id(plan.plan_id, session=db_session)
    assert fetched is not None
    assert fetched.plan_id == plan.plan_id

    missing = crud.get_subscription_plan_by_id(999999999, session=db_session)
    assert missing is None

def test_update_subscription_plan_not_found_returns_none(db_session):
    updated = crud.update_subscription_plan(
        plan_id=999999999,
        plan_name="NewName",
        session=db_session,
    )
    assert updated is None

def test_update_subscription_plan_fields(db_session):
    plan = crud.create_subscription_plan("Growth", 1000, 20, "GBP", session=db_session)

    updated = crud.update_subscription_plan(
        plan_id=plan.plan_id,
        plan_name="Growth Plus",
        price_pennies=1500,
        seat_limit=30,
        currency="USD",
        session=db_session,
    )

    assert updated is not None
    assert updated.plan_id == plan.plan_id
    assert updated.plan_name == "Growth Plus"
    assert updated.price_pennies == 1500
    assert updated.seat_limit == 30
    assert updated.currency == "USD"

@pytest.mark.parametrize(
    "kwargs",
    [
        {"plan_name": " "},          # too short after trim
        {"plan_name": "A"},          # length 1
        {"price_pennies": -5},       # negative
        {"seat_limit": 0},           # invalid
        {"currency": "US"},          # invalid
    ],
)

def test_update_subscription_plan_invalid_inputs_raise_valueerror(db_session, kwargs):
    plan = crud.create_subscription_plan("Standard", 500, 10, "GBP", session=db_session)

    with pytest.raises(ValueError):
        crud.update_subscription_plan(
            plan_id=plan.plan_id,
            session=db_session,
            **kwargs,
        )

def test_update_subscription_plan_duplicate_name_raises_runtimeerror(db_session):
    p1 = crud.create_subscription_plan("Plan One", 100, 5, "GBP", session=db_session)
    p2 = crud.create_subscription_plan("Plan Two", 200, 5, "GBP", session=db_session)

    # rename p2 -> p1 name should violate unique
    with pytest.raises(RuntimeError):
        crud.update_subscription_plan(
            plan_id=p2.plan_id,
            plan_name="Plan One",
            session=db_session,
        )

def test_delete_subscription_plan_not_found_returns_false(db_session):
    ok = crud.delete_subscription_plan(999999999, session=db_session)
    assert ok is False

def test_delete_subscription_plan_success(db_session):
    plan = crud.create_subscription_plan("To Delete", 10, 1, "GBP", session=db_session)
    ok = crud.delete_subscription_plan(plan.plan_id, session=db_session)
    assert ok is True

    assert crud.get_subscription_plan_by_id(plan.plan_id, session=db_session) is None
