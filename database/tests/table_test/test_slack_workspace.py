import pytest
from database.services import slack_workspaces_crud as crud 
from database.services import companies_crud as company_crud 
from database.services import subscription_plan_crud as sp_crud 
from database.services import subscriptions_crud as sub_crud 
from database.services import users_crud as user_crud 

from datetime import datetime, timedelta, timezone
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

def _mk_company(db_session, name="SlackCo"):
    return company_crud.create_company(name, session=db_session)

@pytest.mark.parametrize("team_id,token", [("", "x"), ("T123", ""), (" ", "tok"), ("T123", " ")])
def test_create_slack_workspace_invalid_inputs_raise_valueerror(db_session, team_id, token):
    company = _mk_company(db_session)
    with pytest.raises(ValueError):
        crud.create_slack_workspace(company.company_id, team_id=team_id, access_token=token, session=db_session)

def test_create_slack_workspace_success_and_get(db_session):
    company = _mk_company(db_session)
    ws = crud.create_slack_workspace(
        company.company_id,
        team_id="T123",
        access_token="tok1",
        session=db_session,
    )
    assert ws.slack_workspace_id is not None
    assert ws.company_id == company.company_id
    assert ws.team_id == "T123"
    assert ws.revoked_at is None

    by_id = crud.get_slack_workspace_by_id(ws.slack_workspace_id, session=db_session)
    assert by_id is not None
    assert by_id.team_id == "T123"

    by_team = crud.get_slack_workspace_by_team_id("T123", session=db_session)
    assert by_team is not None
    assert by_team.slack_workspace_id == ws.slack_workspace_id

def test_create_slack_workspace_duplicate_team_id_raises_runtimeerror(db_session):
    c1 = _mk_company(db_session, "SlackCo1")
    c2 = _mk_company(db_session, "SlackCo2")

    crud.create_slack_workspace(c1.company_id, team_id="T_DUP", access_token="tok", session=db_session)

    with pytest.raises(RuntimeError):
        crud.create_slack_workspace(c2.company_id, team_id="T_DUP", access_token="tok2", session=db_session)

def test_list_slack_workspaces_include_exclude_revoked(db_session):
    c = _mk_company(db_session)
    crud.create_slack_workspace(c.company_id, team_id="T1", access_token="tok1", session=db_session)
    crud.create_slack_workspace(c.company_id, team_id="T2", access_token="tok2", session=db_session)

    assert crud.revoke_slack_workspace("T2", session=db_session) is True

    all_ws = crud.list_slack_workspaces_for_company(c.company_id, include_revoked=True, session=db_session)
    assert [w.team_id for w in all_ws] == ["T1", "T2"]

    active_ws = crud.list_slack_workspaces_for_company(c.company_id, include_revoked=False, session=db_session)
    assert [w.team_id for w in active_ws] == ["T1"]

def test_update_slack_workspace_access_token(db_session):
    c = _mk_company(db_session)
    crud.create_slack_workspace(c.company_id, team_id="T_UPD", access_token="old", session=db_session)

    updated = crud.update_slack_workspace_access_token("T_UPD", access_token="new", session=db_session)
    assert updated is not None
    assert updated.access_token == "new"

def test_revoke_and_reinstall_slack_workspace(db_session):
    c = _mk_company(db_session)
    crud.create_slack_workspace(c.company_id, team_id="T_REV", access_token="tok", session=db_session)

    assert crud.revoke_slack_workspace("T_REV", session=db_session) is True
    ws = crud.get_slack_workspace_by_team_id("T_REV", session=db_session)
    assert ws is not None
    assert ws.revoked_at is not None

    reinstalled = crud.reinstall_slack_workspace("T_REV", access_token="tok2", session=db_session)
    assert reinstalled is not None
    assert reinstalled.access_token == "tok2"
    assert reinstalled.revoked_at is None

def test_hard_delete_slack_workspace_success(db_session):
    c = _mk_company(db_session)
    crud.create_slack_workspace(c.company_id, team_id="T_DEL", access_token="tok", session=db_session)

    assert crud.hard_delete_slack_workspace("T_DEL", session=db_session) is True
    assert crud.get_slack_workspace_by_team_id("T_DEL", session=db_session) is None

def test_hard_delete_slack_workspace_fails_if_referenced(db_session):
    c = _mk_company(db_session)
    ws = crud.create_slack_workspace(
        c.company_id,
        team_id="T_REF",
        access_token="tok",
        session=db_session,
    )

    plan = sp_crud.create_subscription_plan(
        plan_name="Test Plan",
        price_pennies=1000,
        seat_limit=5,
        session=db_session,
    )

    now = datetime.now(timezone.utc)
    sub_crud.create_subscription(
        c.company_id,
        plan.plan_id,
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        session=db_session,
    )

    u = user_crud.create_user(c.company_id, role="viewer", session=db_session)

    sa = crud.model.SlackAccount(
        company_id=c.company_id,
        team_id=ws.team_id,
        slack_user_id="U123",
        user_id=u.user_id,
        email="user@example.com",
    )
    db_session.add(sa)
    db_session.commit()

    with pytest.raises(RuntimeError):
        crud.hard_delete_slack_workspace("T_REF", session=db_session)