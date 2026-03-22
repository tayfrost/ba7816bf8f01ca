import pytest
from .. import new_crud as crud
from sqlalchemy import event
from datetime import datetime, timezone, timedelta

import inspect

@pytest.fixture()
def db_session():
    connection = crud.engine.connect()
    transaction = connection.begin()
    session = crud.Session(bind=connection)

    # Start a SAVEPOINT. session.commit() will ends the SAVEPOINT
    session.begin_nested()

    # If the SAVEPOINT ends, restart it automatically.
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        try:
            transaction.rollback()
        except Exception:
            pass
        connection.close()

def _mk_period():
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=30)
    return start, end


def _mk_company_and_plan(db_session):
    company = crud.create_company("AcmeSub", session=db_session)
    plan = crud.create_subscription_plan("StarterSub", 0, 5, "GBP", session=db_session)
    return company, plan

def test_create_subscription_success(db_session):
    company, plan = _mk_company_and_plan(db_session)
    start, end = _mk_period()

    sub = crud.create_subscription(
        company_id=company.company_id,
        plan_id=plan.plan_id,
        status="trialing",
        current_period_start=start,
        current_period_end=end,
        session=db_session,
    )

    assert sub.subscription_id is not None
    assert sub.company_id == company.company_id
    assert sub.plan_id == plan.plan_id
    assert sub.status == "trialing"


@pytest.mark.parametrize("bad_status", ["", "paused", "ACTIVE"])
def test_create_subscription_invalid_status_raises_valueerror(db_session, bad_status):
    company, plan = _mk_company_and_plan(db_session)
    start, end = _mk_period()

    with pytest.raises(ValueError):
        crud.create_subscription(
            company_id=company.company_id,
            plan_id=plan.plan_id,
            status=bad_status,
            current_period_start=start,
            current_period_end=end,
            session=db_session,
        )

def test_create_subscription_invalid_period_raises_valueerror(db_session):
    company, plan = _mk_company_and_plan(db_session)
    start = datetime.now(timezone.utc)
    end = start  # not after start

    with pytest.raises(ValueError):
        crud.create_subscription(
            company_id=company.company_id,
            plan_id=plan.plan_id,
            status="trialing",
            current_period_start=start,
            current_period_end=end,
            session=db_session,
        )


def test_create_subscription_one_per_company_enforced(db_session):
    company, plan = _mk_company_and_plan(db_session)
    start, end = _mk_period()

    crud.create_subscription(
        company_id=company.company_id,
        plan_id=plan.plan_id,
        status="trialing",
        current_period_start=start,
        current_period_end=end,
        session=db_session,
    )

    with pytest.raises(RuntimeError):
        crud.create_subscription(
            company_id=company.company_id,
            plan_id=plan.plan_id,
            status="active",
            current_period_start=start,
            current_period_end=end,
            session=db_session,
        )


def test_get_subscription_by_company_id(db_session):
    company, plan = _mk_company_and_plan(db_session)
    start, end = _mk_period()

    sub = crud.create_subscription(
        company_id=company.company_id,
        plan_id=plan.plan_id,
        status="active",
        current_period_start=start,
        current_period_end=end,
        session=db_session,
    )

    got = crud.get_subscription_by_company_id(company.company_id, session=db_session)
    assert got is not None
    assert got.subscription_id == sub.subscription_id


def test_update_subscription_fields(db_session):
    company, plan1 = _mk_company_and_plan(db_session)
    plan2 = crud.create_subscription_plan("ProSub", 1000, 25, "GBP", session=db_session)

    start, end = _mk_period()
    sub = crud.create_subscription(
        company_id=company.company_id,
        plan_id=plan1.plan_id,
        status="trialing",
        current_period_start=start,
        current_period_end=end,
        session=db_session,
    )

    new_start = start + timedelta(days=1)
    new_end = end + timedelta(days=10)

    updated = crud.update_subscription(
        sub.subscription_id,
        plan_id=plan2.plan_id,
        status="active",
        current_period_start=new_start,
        current_period_end=new_end,
        session=db_session,
    )

    assert updated is not None
    assert updated.plan_id == plan2.plan_id
    assert updated.status == "active"
    assert updated.current_period_start == new_start
    assert updated.current_period_end == new_end

def test_cancel_subscription(db_session):
    company, plan = _mk_company_and_plan(db_session)
    start, end = _mk_period()

    sub = crud.create_subscription(
        company_id=company.company_id,
        plan_id=plan.plan_id,
        status="active",
        current_period_start=start,
        current_period_end=end,
        session=db_session,
    )

    assert crud.cancel_subscription(sub.subscription_id, session=db_session) is True
    got = crud.get_subscription_by_id(sub.subscription_id, session=db_session)
    assert got is not None
    assert got.status == "canceled"


def test_delete_subscription(db_session):
    company, plan = _mk_company_and_plan(db_session)
    start, end = _mk_period()

    sub = crud.create_subscription(
        company_id=company.company_id,
        plan_id=plan.plan_id,
        status="active",
        current_period_start=start,
        current_period_end=end,
        session=db_session,
    )

    assert crud.delete_subscription(sub.subscription_id, session=db_session) is True
    assert crud.get_subscription_by_id(sub.subscription_id, session=db_session) is None