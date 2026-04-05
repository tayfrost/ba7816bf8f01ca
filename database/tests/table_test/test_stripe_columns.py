"""
Tests that the Stripe columns added to companies and subscription_plans
work correctly and don't break existing functionality.
"""

import pytest
from database.services import companies_crud as company_crud
from database.services import subscription_plan_crud as plan_crud
from database.database import models as model
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False)


@pytest.fixture
def db_session():
    connection = company_crud.engine.connect()
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


# ====================== COMPANY: stripe_customer_id =======================

def test_create_company_without_stripe_customer_id(db_session):
    """Company creation still works — stripe_customer_id defaults to None."""
    c = company_crud.create_company("StripeTestCo", session=db_session)
    assert c.company_id is not None
    assert c.stripe_customer_id is None


def test_set_stripe_customer_id_on_company(db_session):
    """stripe_customer_id can be set and read back."""
    c = company_crud.create_company("PaymentCo", session=db_session)
    c.stripe_customer_id = "cus_test_abc123"
    db_session.flush()
    db_session.refresh(c)
    assert c.stripe_customer_id == "cus_test_abc123"


def test_stripe_customer_id_unique_constraint(db_session):
    """Two companies cannot share the same stripe_customer_id."""
    c1 = company_crud.create_company("CompanyOne", session=db_session)
    c1.stripe_customer_id = "cus_unique_123"
    db_session.flush()

    c2 = company_crud.create_company("CompanyTwo", session=db_session)
    c2.stripe_customer_id = "cus_unique_123"

    with pytest.raises(Exception):  # IntegrityError
        db_session.flush()


# ====================== SUBSCRIPTION PLAN: stripe_price_ids ================

def test_create_plan_without_stripe_price_ids(db_session):
    """Plan creation still works — Stripe price IDs default to None."""
    plan = plan_crud.create_subscription_plan(
        plan_name="BasicPlan",
        price_pennies=4900,
        seat_limit=10,
        currency="GBP",
        session=db_session,
    )
    assert plan.plan_id is not None
    assert plan.stripe_price_id_monthly is None
    assert plan.stripe_price_id_yearly is None


def test_set_stripe_price_ids_on_plan(db_session):
    """Stripe price IDs can be set and read back."""
    plan = plan_crud.create_subscription_plan(
        plan_name="ProPlan",
        price_pennies=14900,
        seat_limit=50,
        currency="GBP",
        session=db_session,
    )
    plan.stripe_price_id_monthly = "price_monthly_abc"
    plan.stripe_price_id_yearly = "price_yearly_xyz"
    db_session.flush()
    db_session.refresh(plan)

    assert plan.stripe_price_id_monthly == "price_monthly_abc"
    assert plan.stripe_price_id_yearly == "price_yearly_xyz"


def test_existing_crud_functions_unaffected(db_session):
    """All existing CRUD operations still work with the new columns present."""
    # Company CRUD
    c = company_crud.create_company("CrudTestCo", session=db_session)
    assert company_crud.get_company_by_id(c.company_id, session=db_session) is not None
    assert company_crud.get_company_by_name("CrudTestCo", session=db_session) is not None

    updated = company_crud.update_company(c.company_id, name="CrudTestCoRenamed", session=db_session)
    assert updated.name == "CrudTestCoRenamed"

    # Subscription plan CRUD
    plan = plan_crud.create_subscription_plan("CrudPlan", 999, 5, "GBP", session=db_session)
    assert plan_crud.get_subscription_plan_by_id(plan.plan_id, session=db_session) is not None
    assert plan_crud.get_subscription_plan_by_name("CrudPlan", session=db_session) is not None

    updated_plan = plan_crud.update_subscription_plan(
        plan.plan_id, plan_name="CrudPlanUpdated", session=db_session
    )
    assert updated_plan.plan_name == "CrudPlanUpdated"
