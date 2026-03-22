import pytest
from backend import crud
from sqlalchemy import event

import inspect

def test_debug_update_signature():
    print(inspect.signature(crud.update_sub_plan))

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


# -------------------- CRUD validation tests (ValueError) --------------------

@pytest.mark.parametrize(
    "p_name,cost,max_emp,currency",
    [
        (" ", 0, 5, "GBP"),          # name too short after trim
        ("A", 0, 5, "GBP"),          # name length 1
        ("Valid", -1, 5, "GBP"),     # negative cost
        ("Valid", 0, 0, "GBP"),      # max_employees <= 0
        ("Valid", 0, 5, "GB"),       # currency not length 3
        ("Valid", 0, 5, None),       # currency invalid (will become "GBP")
    ],
)

def test_create_sub_plan_validation_errors(db_session, p_name, cost, max_emp, currency):
    if currency is None:
        pytest.skip("currency=None becomes default 'GBP' in create_sub_plan; not a validation error.")
    with pytest.raises(ValueError):
        crud.create_sub_plan(p_name, cost, max_emp, currency=currency, session=db_session)


def test_create_sub_plan_default_currency_when_none(db_session):
    plan = crud.create_sub_plan("DefaultCur", 0, 5, currency=None, session=db_session)
    assert plan.currency.strip() == "GBP"

def test_create_sub_plan_default_currency_when_empty_string(db_session):
    plan = crud.create_sub_plan("EmptyCur", 0, 5, currency="", session=db_session)
    assert plan.currency.strip() == "GBP"

# -------------------- Create / Read --------------------

def test_create_plan_success(db_session):
    plan = crud.create_sub_plan("Starter", 0, 5, "GBP", session=db_session)
    assert plan.plan_id is not None
    assert plan.plan_name == "Starter"
    assert plan.plan_cost_pennies == 0
    assert plan.max_employees == 5
    assert plan.currency.strip() == "GBP"


def test_read_all_returns_created(db_session):
    crud.create_sub_plan("Pro", 1000, 10, "GBP", session=db_session)
    plans = crud.read_all(session=db_session)
    assert any(p.plan_name == "Pro" for p in plans)


def test_get_by_name(db_session):
    crud.create_sub_plan("Team", 2500, 25, "GBP", session=db_session)
    p = crud.get_sub_plan_by_name("Team", session=db_session)
    assert p is not None
    assert p.plan_name == "Team"


# -------------------- Duplicate handling --------------------

def test_create_duplicate_name_raises_runtimeerror(db_session):
    crud.create_sub_plan("Business", 5000, 50, "GBP", session=db_session)

    with pytest.raises(RuntimeError) as exc:
        crud.create_sub_plan("Business", 6000, 60, "GBP", session=db_session)

    assert "already exists" in str(exc.value)


# -------------------- Update --------------------

def test_update_plan_success(db_session):
    plan = crud.create_sub_plan("Scale", 100, 5, "GBP", session=db_session)

    updated = crud.update_sub_plan(
        plan.plan_id,
        plan_cost_pennies=200,
        max_employees=10,
        session=db_session,
    )
    assert updated is not None
    assert updated.plan_cost_pennies == 200
    assert updated.max_employees == 10

def test_update_plan_validation_error(db_session):
    plan = crud.create_sub_plan("ValUpdate", 100, 5, "GBP", session=db_session)
    plan_id = plan.plan_id 

    with pytest.raises(ValueError):
        crud.update_sub_plan(plan_id, plan_cost_pennies=-1, session=db_session)

    with pytest.raises(ValueError):
        crud.update_sub_plan(plan_id, max_employees=0, session=db_session)

    with pytest.raises(ValueError):
        crud.update_sub_plan(plan_id, currency="US", session=db_session)

    with pytest.raises(ValueError):
        crud.update_sub_plan(plan_id, plan_name=" ", session=db_session)


# -------------------- Delete --------------------

def test_delete_plan_success(db_session):
    plan = crud.create_sub_plan("DeleteMe", 1, 1, "GBP", session=db_session)
    assert crud.delete_sub_plan(plan.plan_id, session=db_session) is True
    assert crud.get_sub_plan_by_name("DeleteMe", session=db_session) is None


def test_delete_missing_plan_returns_false(db_session):
    assert crud.delete_sub_plan(999999999999, session=db_session) is False