import pytest
from backend import crud
from backend import alchemy_oop as model
from sqlalchemy import event, delete, update, text
from sqlalchemy.exc import DBAPIError

@pytest.fixture()
def db_session():
    connection = crud.engine.connect()
    transaction = connection.begin()
    session = crud.Session(bind=connection)

    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()

def _make_plan(session, name="StarterPlan"):
    return crud.create_sub_plan(name, 0, 5, "GBP", session=session)

def _make_company(session, plan_id, name="Acme Ltd"):
    return crud.create_company(plan_id=plan_id, company_name=name, session=session)

def _make_workspace(session, company_id, team_id="T123", token="xoxb-1"):
    return crud.create_workspace(company_id=company_id, team_id=team_id, access_token=token, session=session)

def test_create_slack_user_success(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    ws = _make_workspace(db_session, company.company_id, team_id="TSU1")

    su = crud.create_slack_user(
        team_id=ws.team_id,
        slack_user_id="U123",
        name="John",
        surname="Smith",
        status="active",
        session=db_session,
    )

    assert su.id is not None
    assert su.team_id == "TSU1"
    assert su.slack_user_id == "U123"
    assert su.status == "active"


def test_create_slack_user_requires_workspace(db_session):
    with pytest.raises(ValueError):
        crud.create_slack_user("NO_TEAM", "U1", "John", "Smith", session=db_session)

def test_create_slack_user_validates_inputs(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    ws = _make_workspace(db_session, company.company_id, team_id="TSU2")

    with pytest.raises(ValueError):
        crud.create_slack_user("", "U1", "John", "Smith", session=db_session)
    with pytest.raises(ValueError):
        crud.create_slack_user(ws.team_id, "", "John", "Smith", session=db_session)
    with pytest.raises(ValueError):
        crud.create_slack_user(ws.team_id, "U1", "J", "Smith", session=db_session)   # name too short
    with pytest.raises(ValueError):
        crud.create_slack_user(ws.team_id, "U1", "John", "S", session=db_session)   # surname too short
    with pytest.raises(ValueError):
        crud.create_slack_user(ws.team_id, "U1", "John", "Smith", status="bad", session=db_session)

def test_create_slack_user_unique_team_and_user(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    ws = _make_workspace(db_session, company.company_id, team_id="TSU3")

    crud.create_slack_user(ws.team_id, "U999", "John", "Smith", session=db_session)

    # same (team_id, slack_user_id) should violate uq_slack_users_team_user -> RuntimeError wrapper
    with pytest.raises(RuntimeError) as e:
        crud.create_slack_user(ws.team_id, "U999", "Jane", "Doe", session=db_session)
    assert "create_slack_user" in str(e.value)


def test_get_slack_user_by_id_and_team_slack_id(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    ws = _make_workspace(db_session, company.company_id, team_id="TSU4")

    su = crud.create_slack_user(ws.team_id, "U1", "John", "Smith", session=db_session)

    by_id = crud.get_slack_user_by_id(su.id, session=db_session)
    assert by_id is not None
    assert by_id.slack_user_id == "U1"

    by_key = crud.get_slack_user_by_team_and_slack_id(ws.team_id, "U1", session=db_session)
    assert by_key is not None
    assert by_key.id == su.id

def test_get_slack_user_missing_returns_none(db_session):
    assert crud.get_slack_user_by_id(99999999, session=db_session) is None
    assert crud.get_slack_user_by_team_and_slack_id("T_NO", "U_NO", session=db_session) is None

def test_get_slack_user_by_team_and_slack_id_validates_inputs(db_session):
    with pytest.raises(ValueError):
        crud.get_slack_user_by_team_and_slack_id("", "U1", session=db_session)
    with pytest.raises(ValueError):
        crud.get_slack_user_by_team_and_slack_id("T1", "", session=db_session)

def test_list_slack_users_for_workspace(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    ws = _make_workspace(db_session, company.company_id, team_id="TSU5")

    crud.create_slack_user(ws.team_id, "U1", "John", "Smith", status="active", session=db_session)
    crud.create_slack_user(ws.team_id, "U2", "Jane", "Doe", status="inactive", session=db_session)
    crud.create_slack_user(ws.team_id, "U3", "Alan", "Turing", status="removed", session=db_session)

    all_users = crud.list_slack_users_for_workspace(ws.team_id, session=db_session)
    assert [u.slack_user_id for u in all_users] == ["U1", "U2", "U3"]

    active_users = crud.list_slack_users_for_workspace(ws.team_id, status="active", session=db_session)
    assert [u.slack_user_id for u in active_users] == ["U1"]


def test_list_slack_users_for_workspace_validates_inputs(db_session):
    with pytest.raises(ValueError):
        crud.list_slack_users_for_workspace("", session=db_session)
    with pytest.raises(ValueError):
        crud.list_slack_users_for_workspace("T1", status="bad", session=db_session)

def test_update_slack_user_profile_success(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    ws = _make_workspace(db_session, company.company_id, team_id="TSU6")

    crud.create_slack_user(ws.team_id, "U1", "John", "Smith", session=db_session)

    updated = crud.update_slack_user_profile(ws.team_id, "U1", name="Johnny", session=db_session)
    assert updated.name == "Johnny"
    assert updated.surname == "Smith"

    updated2 = crud.update_slack_user_profile(ws.team_id, "U1", surname="Smythe", session=db_session)
    assert updated2.name == "Johnny"
    assert updated2.surname == "Smythe"


def test_update_slack_user_profile_requires_fields(db_session):
    with pytest.raises(ValueError):
        crud.update_slack_user_profile("T1", "U1", session=db_session)


def test_update_slack_user_profile_validates_and_not_found(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    ws = _make_workspace(db_session, company.company_id, team_id="TSU7")
    team_id = ws.team_id

    with pytest.raises(ValueError):
        crud.update_slack_user_profile(team_id, "U404", name="Johnny", session=db_session)

    crud.create_slack_user(team_id, "U1", "John", "Smith", session=db_session)

    with pytest.raises(ValueError):
        crud.update_slack_user_profile(team_id, "U1", name="J", session=db_session)  # too short
    with pytest.raises(ValueError):
        crud.update_slack_user_profile(team_id, "U1", surname="S", session=db_session)

        

def test_set_slack_user_status_success(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    ws = _make_workspace(db_session, company.company_id, team_id="TSU8")

    crud.create_slack_user(ws.team_id, "U1", "John", "Smith", status="active", session=db_session)

    su = crud.set_slack_user_status(ws.team_id, "U1", "inactive", session=db_session)
    assert su.status == "inactive"

    su2 = crud.set_slack_user_status(ws.team_id, "U1", "removed", session=db_session)
    assert su2.status == "removed"


def test_set_slack_user_status_validates_and_not_found(db_session):
    with pytest.raises(ValueError):
        crud.set_slack_user_status("", "U1", "active", session=db_session)
    with pytest.raises(ValueError):
        crud.set_slack_user_status("T1", "", "active", session=db_session)
    with pytest.raises(ValueError):
        crud.set_slack_user_status("T1", "U1", "bad", session=db_session)

    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    ws = _make_workspace(db_session, company.company_id, team_id="TSU9")

    with pytest.raises(ValueError):
        crud.set_slack_user_status(ws.team_id, "U404", "active", session=db_session)


def test_upsert_slack_user_inserts_then_updates(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    ws = _make_workspace(db_session, company.company_id, team_id="TSU10")

    su1 = crud.upsert_slack_user(ws.team_id, "U1", "John", "Smith", status="active", session=db_session)
    assert su1.id is not None
    assert su1.name == "John"
    assert su1.status == "active"

    su2 = crud.upsert_slack_user(ws.team_id, "U1", "Johnny", "Smythe", status="inactive", session=db_session)
    assert su2.id == su1.id
    assert su2.name == "Johnny"
    assert su2.surname == "Smythe"
    assert su2.status == "inactive"


def test_upsert_slack_user_requires_workspace(db_session):
    with pytest.raises(ValueError):
        crud.upsert_slack_user("NO_TEAM", "U1", "John", "Smith", session=db_session)


def test_upsert_slack_user_validates_inputs(db_session):
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    ws = _make_workspace(db_session, company.company_id, team_id="TSU11")

    with pytest.raises(ValueError):
        crud.upsert_slack_user("", "U1", "John", "Smith", session=db_session)
    with pytest.raises(ValueError):
        crud.upsert_slack_user(ws.team_id, "", "John", "Smith", session=db_session)
    with pytest.raises(ValueError):
        crud.upsert_slack_user(ws.team_id, "U1", "J", "Smith", session=db_session)
    with pytest.raises(ValueError):
        crud.upsert_slack_user(ws.team_id, "U1", "John", "S", session=db_session)
    with pytest.raises(ValueError):
        crud.upsert_slack_user(ws.team_id, "U1", "John", "Smith", status="bad", session=db_session)


def test_hard_delete_slack_user_by_team_and_slack_id(db_session):
   
    plan = _make_plan(db_session)
    company = _make_company(db_session, plan.plan_id)
    ws = _make_workspace(db_session, company.company_id, team_id="TSU12")

    crud.create_slack_user(ws.team_id, "U1", "John", "Smith", session=db_session)

    crud.hard_delete_slack_user(ws.team_id, "U1", session=db_session)

    assert crud.get_slack_user_by_team_and_slack_id(ws.team_id, "U1", session=db_session) is None