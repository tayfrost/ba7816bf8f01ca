import pytest
from backend import crud
from sqlalchemy import event

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
        transaction.rollback()
        connection.close()

def _make_plan(session, name="StarterPlan"):
    return crud.create_sub_plan(name, 0, 5, "GBP", session=session)

# -------------------- Create --------------------

def test_create_company_success(db_session):
    plan = _make_plan(db_session, "PlanA")
    company = crud.create_company(plan.plan_id, "Derja Ltd", session=db_session)

    assert company.company_id is not None
    assert company.plan_id == plan.plan_id
    assert company.company_name == "Derja Ltd"
    assert company.deleted_at is None
    assert company.created_at is not None


def test_create_company_validation_error_name(db_session):
    plan = _make_plan(db_session, "PlanB")

    with pytest.raises(ValueError):
        crud.create_company(plan.plan_id, " ", session=db_session)

    with pytest.raises(ValueError):
        crud.create_company(plan.plan_id, "A", session=db_session)


def test_create_company_plan_not_found(db_session):
    with pytest.raises(ValueError) as exc:
        crud.create_company(999999999999, "Nope Ltd", session=db_session)
    assert "not found" in str(exc.value).lower()


def test_create_company_by_plan_name_success(db_session):
    _make_plan(db_session, "PlanByName")
    company = crud.create_company_by_plan_name("PlanByName", "Beta Ltd", session=db_session)

    assert company.company_id is not None
    assert company.company_name == "Beta Ltd"


def test_create_company_by_plan_name_plan_missing(db_session):
    with pytest.raises(ValueError):
        crud.create_company_by_plan_name("DoesNotExist", "Gamma Ltd", session=db_session)


# -------------------- Get / List --------------------

def test_get_company_by_id(db_session):
    plan = _make_plan(db_session, "PlanC")
    company = crud.create_company(plan.plan_id, "Co1", session=db_session)

    fetched = crud.get_company_by_id(company.company_id, session=db_session)
    assert fetched is not None
    assert fetched.company_id == company.company_id


def test_list_companies_excludes_deleted_by_default(db_session):
    plan = _make_plan(db_session, "PlanD")

    c1 = crud.create_company(plan.plan_id, "AliveCo", session=db_session)
    c2 = crud.create_company(plan.plan_id, "DeletedCo", session=db_session)
    assert crud.soft_delete_company(c2.company_id, session=db_session) is True

    companies = crud.list_companies(session=db_session)
    ids = {c.company_id for c in companies}
    assert c1.company_id in ids
    assert c2.company_id not in ids

    companies_inc = crud.list_companies(include_deleted=True, session=db_session)
    ids_inc = {c.company_id for c in companies_inc}
    assert c2.company_id in ids_inc


# -------------------- Update --------------------

def test_update_company_name_success(db_session):
    plan = _make_plan(db_session, "PlanE")
    company = crud.create_company(plan.plan_id, "OldName", session=db_session)

    updated = crud.update_company(company.company_id, company_name="NewName", session=db_session)
    assert updated is not None
    assert updated.company_name == "NewName"


def test_update_company_plan_success(db_session):
    p1 = _make_plan(db_session, "PlanF1")
    p2 = _make_plan(db_session, "PlanF2")
    company = crud.create_company(p1.plan_id, "SwitchPlanCo", session=db_session)

    updated = crud.update_company(company.company_id, plan_id=p2.plan_id, session=db_session)
    assert updated is not None
    assert updated.plan_id == p2.plan_id


def test_update_company_validation_error(db_session):
    plan = _make_plan(db_session, "PlanG")
    company = crud.create_company(plan.plan_id, "ValidName", session=db_session)

    with pytest.raises(ValueError):
        crud.update_company(company.company_id, company_name=" ", session=db_session)

    with pytest.raises(ValueError):
        crud.update_company(company.company_id, plan_id=999999999999, session=db_session)


def test_update_company_returns_none_when_deleted(db_session):
    plan = _make_plan(db_session, "PlanH")
    company = crud.create_company(plan.plan_id, "ToDelete", session=db_session)
    assert crud.soft_delete_company(company.company_id, session=db_session) is True

    updated = crud.update_company(company.company_id, company_name="Nope", session=db_session)
    assert updated is None


# -------------------- Soft delete --------------------

def test_soft_delete_company(db_session):
    plan = _make_plan(db_session, "PlanI")
    company = crud.create_company(plan.plan_id, "SoftDel", session=db_session)

    assert crud.soft_delete_company(company.company_id, session=db_session) is True
    assert crud.soft_delete_company(company.company_id, session=db_session) is False  # already deleted

    # not returned by default
    assert crud.get_company_by_id(company.company_id, session=db_session) is None
    # returned if include_deleted
    assert crud.get_company_by_id(company.company_id, include_deleted=True, session=db_session) is not None


# -------------------- Hard delete --------------------

def test_hard_delete_company_success(db_session):
    plan = _make_plan(db_session, "PlanJ")
    company = crud.create_company(plan.plan_id, "HardDel", session=db_session)

    assert crud.hard_delete_company(company.company_id, session=db_session) is True
    assert crud.get_company_by_id(company.company_id, include_deleted=True, session=db_session) is None


def test_hard_delete_company_returns_false_if_missing(db_session):
    assert crud.hard_delete_company(999999999999, session=db_session) is False